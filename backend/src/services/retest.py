import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy import select, update
from redis import Redis
from ..config.settings import REDIS_URL,CONFIG
from ..models.retest import RetestStudy
from ..models.source import Source
from ..models.record import Record
from ..utils.serialization import row, now
from .audit import log
from .runs import get_run
from . import retest_algorithm as algo
queue = Redis.from_url(REDIS_URL)
LEASE_SECONDS = 120


def _records(db, source_id):
    return [{'reference': r.reference, 'values': r.values} for r in db.scalars(select(Record).where(Record.source_id == source_id).order_by(Record.id))]


def _source(db, source_id):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404, '未找到复测来源批次')
    return s


def build_snapshot(db, data):
    early = get_run(db, data.early_run_id)
    if early.state != 'completed' or not early.result:
        raise HTTPException(409, '早期密度研究尚未完成，无法冻结分区与尺度')
    if CONFIG['algorithm'] != 'density' or early.result.get('columns', [])[:1] != ['reference'] or 'clusters' not in early.result:
        raise HTTPException(422, '早期研究不是密度分区结果，无法沿用分区')
    if early.result.get('standardization', {}).get('scale') is None:
        raise HTTPException(422, '早期结果缺少标准化尺度，无法沿用')
    if data.period1_source_id == data.period2_source_id:
        raise HTTPException(422, '两期复测必须来自不同来源批次')
    first, second = _source(db, data.period1_source_id), _source(db, data.period2_source_id)
    p1, p2 = _records(db, first.id), _records(db, second.id)
    if not p1 or not p2:
        raise HTTPException(422, '两期来源都必须包含样本')
    early_rows = [{'reference': r['reference'], 'cluster': r['cluster']} for r in early.result['rows']]
    snapshot = {
        'early': {'run_id': early.id, 'run_name': early.name, 'source_id': early.source_id,
                  'parameters': early.parameters, 'checksum': early.result.get('checksum', ''),
                  'standardization': {'mean': early.result['standardization']['mean'],
                                      'scale': early.result['standardization']['scale']},
                  'rows': early_rows},
        'period1': {'source_id': first.id, 'source_name': first.name, 'filename': first.filename, 'records': p1},
        'period2': {'source_id': second.id, 'source_name': second.name, 'filename': second.filename, 'records': p2},
        'parameters': {'pairing': 'suffix', 'seed': algo.SEED, 'permutations': algo.PERMUTATIONS,
                       'full_enum_threshold': algo.FULL_ENUM_THRESHOLD,
                       'min_pairs': algo.MIN_PAIRS, 'alpha': algo.ALPHA, 'features': algo.FEATURES},
        'frozen_at': now(),
    }
    return snapshot


def create_study(db, user, data):
    snapshot = build_snapshot(db, data)
    scale = snapshot['early']['standardization']['scale']
    pairs = algo.build_pairs(snapshot['early']['rows'], snapshot['period1']['records'], snapshot['period2']['records'], scale)
    if not pairs['pairs']:
        raise HTTPException(422, '两期没有可按站号配对的样本')
    grouped = algo.group_pairs(pairs['pairs'], all_zones=algo.early_zones(snapshot['early']['rows']))
    if not grouped['zones']:
        raise HTTPException(422, '没有分区含可配对站，无法进行置换检验')
    plan = algo.plan_permutations(grouped['n'])
    study = RetestStudy(name=data.name, early_run_id=data.early_run_id,
                        period1_source_id=data.period1_source_id, period2_source_id=data.period2_source_id,
                        pairing='suffix', state='queued', parameters=snapshot['parameters'],
                        snapshot=snapshot, progress={'mode': plan['mode'], 'n': plan['n'], 'total': plan['total'],
                                                     'batches': plan['batches'], 'batch_size': plan['batch_size'],
                                                     'threshold': plan['threshold'], 'seed': plan['seed'],
                                                     'done': {}, 'exceed': {}},
                        created_at=now(), updated_at=now())
    db.add(study); db.flush(); log(db, user, 'retest.queued', study.id, study.name); db.commit()
    try:
        queue.rpush('retest:queue', study.id)
    except Exception:
        study.state = 'failed'; study.error = '队列暂不可用，请重试'; db.commit()
        raise HTTPException(503, study.error)
    return row(study)


def list_studies(db, user):
    studies = list(db.scalars(select(RetestStudy).order_by(RetestStudy.id.desc())))
    out = []
    for s in studies:
        d = {k: v for k, v in row(s).items() if k not in ('snapshot', 'result', 'verification', 'run_token')}
        d['priority_zones'] = s.result.get('priority_zones', []) if s.state == 'published' and s.result else []
        out.append(d)
    return out


def get_study(db, id, user):
    s = db.get(RetestStudy, id)
    if not s:
        raise HTTPException(404, '未找到复测研究')
    d = row(s)
    d.pop('run_token', None)
    d.pop('snapshot', None)
    if s.state not in ('verified', 'published'):
        d.pop('result', None)
    if s.state not in ('verified', 'published', 'failed'):
        d.pop('verification', None)
    return d


def retry(db, user, id):
    s = db.get(RetestStudy, id)
    if not s:
        raise HTTPException(404, '未找到复测研究')
    if s.state not in ('failed', 'queued') and not (s.state == 'running' and (s.heartbeat_at or '') < _stale_cutoff()):
        raise HTTPException(409, '仅失败或已中断（租约过期）的复测可重新入队')
    s.state = 'queued'; s.error = ''; s.run_token = ''; s.updated_at = now()
    log(db, user, 'retest.requeued', id)
    db.commit()
    try:
        queue.rpush('retest:queue', id)
    except Exception:
        s.state = 'failed'; s.error = '队列暂不可用，请重试'; db.commit()
        raise HTTPException(503, s.error)
    return {k: v for k, v in row(s).items() if k not in ('snapshot', 'result', 'verification', 'run_token')}


def _stale_cutoff():
    return (datetime.now(timezone.utc) - timedelta(seconds=LEASE_SECONDS)).isoformat()


def claim(db, id):
    """原子认领：同一任务同时只有一个 worker 持有租约，重复投递不会重复计入。"""
    token = secrets.token_hex(16)
    stamp = now()
    result = db.execute(update(RetestStudy).where(
        RetestStudy.id == id,
        (RetestStudy.state == 'queued') |
        ((RetestStudy.state == 'running') & (RetestStudy.heartbeat_at < _stale_cutoff()))
    ).values(state='running', run_token=token, heartbeat_at=stamp, updated_at=stamp))
    db.commit()
    if result.rowcount != 1:
        return None
    return token


def _touch(db, id, token):
    result = db.execute(update(RetestStudy).where(RetestStudy.id == id, RetestStudy.run_token == token,
                                                   RetestStudy.state == 'running').values(heartbeat_at=now()))
    db.commit()
    return result.rowcount == 1


def _save_progress(db, id, token, progress):
    result = db.execute(update(RetestStudy).where(RetestStudy.id == id, RetestStudy.run_token == token,
                                                   RetestStudy.state == 'running').values(progress=progress, heartbeat_at=now(), updated_at=now()))
    db.commit()
    return result.rowcount == 1


def run_study(db, id):
    """执行/恢复一次复测：逐批置换，每批完成即持久化；已完成的批次跳过。"""
    token = claim(db, id)
    if not token:
        return False
    s = db.get(RetestStudy, id)
    try:
        snapshot = s.snapshot
        scale = snapshot['early']['standardization']['scale']
        pairs = algo.build_pairs(snapshot['early']['rows'], snapshot['period1']['records'], snapshot['period2']['records'], scale)
        grouped = algo.group_pairs(pairs['pairs'], all_zones=algo.early_zones(snapshot['early']['rows']))
        if not grouped['zones']:
            raise ValueError('没有分区达到最少配对站数，无法进行置换检验')
        observed = algo.observed_statistics(pairs['pairs'], grouped, scale)
        thresholds = {r['zone']: r['max_abs'] for r in observed}
        plan = algo.plan_permutations(grouped['n'])
        progress = s.progress or {}
        if progress.get('n') != plan['n'] or progress.get('mode') != plan['mode']:
            progress = {'mode': plan['mode'], 'n': plan['n'], 'total': plan['total'], 'batches': plan['batches'],
                        'batch_size': plan['batch_size'], 'threshold': plan['threshold'], 'seed': plan['seed'],
                        'done': {}, 'exceed': {}}
        done = progress.setdefault('done', {})
        exceed = progress.setdefault('exceed', {})
        for batch in range(plan['batches']):
            key = str(batch)
            if key in done:
                continue
            if not _touch(db, id, token):
                return False
            signs = algo.batch_signs(plan, batch)
            counts = algo.batch_exceedance(signs, grouped['deltas'], grouped['zone_indices'], thresholds)
            done[key] = {str(z): counts[z] for z in counts}
            for z, c in counts.items():
                exceed[str(z)] = exceed.get(str(z), 0) + int(c)
            progress['batches_done'] = len(done)
            if not _save_progress(db, id, token, progress):
                return False
        if len(done) != plan['batches']:
            raise ValueError('置换批次不完整，请重新入队')
        total = plan['total']
        result = _assemble(snapshot, pairs, grouped, observed, exceed, plan)
        s = db.get(RetestStudy, id)
        if not s or s.run_token != token:
            return False
        verification = verify_payload(snapshot, result)
        s.result = result
        s.verification = verification
        s.state = 'verified' if verification['passed'] else 'failed'
        s.error = '' if verification['passed'] else '结果核对未通过：' + '；'.join(verification['failures'])
        s.run_token = ''; s.updated_at = now()
        log(db, 'worker', 'retest.verified' if verification['passed'] else 'retest.failed', id, verification['summary'])
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        s = db.get(RetestStudy, id)
        if s and s.run_token == token:
            s.state = 'failed'; s.error = str(exc)[:2000]; s.run_token = ''; s.updated_at = now()
            log(db, 'worker', 'retest.failed', id, s.error)
            db.commit()
        return False


def _assemble(snapshot, pairs, grouped, observed, exceed, plan):
    scale = snapshot['early']['standardization']['scale']
    total = plan['total']
    zones = []
    exact = plan['mode'] == 'full_enumeration'
    for row_ in observed:
        count = int(exceed.get(str(row_['zone']), 0))
        p = algo.corrected_p(count, total, exact)
        zones.append({**row_, 'exceedances': count, 'p_value': p, 'priority': p < algo.ALPHA})
    priority = sorted([z for z in zones if z['priority']], key=lambda z: z['p_value'])
    return {
        'zones': zones,
        'priority_zones': [{'zone': z['zone'], 'n': z['n'], 'max_feature': z['max_feature'],
                            'max_abs': z['max_abs'], 'means': z['means'], 'means_raw': z['means_raw'],
                            'p_value': z['p_value']} for z in priority],
        'excluded_zones': grouped['insufficient'],
        'pairing': {'paired': len(pairs['pairs']), 'pairs': pairs['pairs'], 'unmatched': pairs['unmatched'],
                    'unzoned': pairs['unzoned'], 'invalid': pairs['invalid'], 'conflicts': pairs['conflicts']},
        'permutation': {'mode': plan['mode'], 'n': plan['n'], 'total': total, 'seed': plan['seed'],
                        'threshold': plan['threshold'], 'batches': plan['batches']},
        'alpha': algo.ALPHA,
        'method': ('站号取样本编号末尾数字，编号不含数字时用编号本身；两期按站号配对。分区与标准化尺度沿用早期密度结果。'
                   '每区统计量为三项标准化平均变化的最大绝对值；置换时同站三项一起换期，'
                   '每次置换取全区最大统计量，据此校正各区 p 值。'),
        'checksum': algo.checksum(snapshot),
    }


def verify_payload(snapshot, result):
    """独立复核：配对依据、分区归属、观测统计量与 p 值必须能从冻结快照重算一致。"""
    checks, failures = [], []
    scale = snapshot['early']['standardization']['scale']
    early_rows = snapshot['early']['rows']
    recomputed = algo.build_pairs(early_rows, snapshot['period1']['records'], snapshot['period2']['records'], scale)
    grouped = algo.group_pairs(recomputed['pairs'], all_zones=algo.early_zones(early_rows))
    observed = algo.observed_statistics(recomputed['pairs'], grouped, scale)

    def check(name, ok, detail=''):
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail})
        if not ok:
            failures.append(name)

    check('配对站数一致', len(recomputed['pairs']) == result['pairing']['paired'],
          f"重算{len(recomputed['pairs'])}站")
    stored_pairs = {p['station']: p for p in result['pairing']['pairs']}
    zone_ok = all(stored_pairs.get(p['station'], {}).get('zone') == p['zone'] for p in recomputed['pairs'])
    check('分区归属与早期结果一致', zone_ok)
    early_zone = {r['reference']: int(r['cluster']) for r in early_rows}
    check('无噪声站被纳入检验', all(p['zone'] >= 0 and p['zone'] == early_zone.get(p['early_reference']) for p in recomputed['pairs']))
    recompute_zones = {r['zone']: r for r in observed}
    check('分区数量一致', sorted(recompute_zones) == sorted(z['zone'] for z in result['zones']))
    stat_ok = True
    for zone in result['zones']:
        ref = recompute_zones.get(zone['zone'])
        if not ref or abs(ref['max_abs'] - zone['max_abs']) > 1e-9:
            stat_ok = False
        if any(abs(ref['means'][f] - zone['means'][f]) > 1e-9 for f in algo.FEATURES):
            stat_ok = False
    check('各区三项均值与最大绝对值可重算', stat_ok)
    total = result['permutation']['total']
    exact = result['permutation']['mode'] == 'full_enumeration'
    p_ok = True
    for zone in result['zones']:
        if abs(algo.corrected_p(zone['exceedances'], total, exact) - zone['p_value']) > 1e-12:
            p_ok = False
        if zone['priority'] != (zone['p_value'] < result['alpha']):
            p_ok = False
    check('校正 p 值与优先标记一致', p_ok)
    plan = algo.plan_permutations(grouped['n'])
    thresholds = {r['zone']: r['max_abs'] for r in observed}
    replay = {zone: 0 for zone in grouped['zones']}
    for batch in range(plan['batches']):
        counts = algo.batch_exceedance(algo.batch_signs(plan, batch), grouped['deltas'],
                                       grouped['zone_indices'], thresholds)
        for zone, count in counts.items():
            replay[zone] += int(count)
    check('置换超限次数可独立重放', all(replay[z['zone']] == z['exceedances'] for z in result['zones']),
          ' / '.join(f"区{z}: 重放 {replay[z['zone']]} vs 记录 {z['exceedances']}" for z in result['zones']))
    params = snapshot['parameters']
    mode = result['permutation']['mode']
    expected_total = 2 ** result['permutation']['n'] if mode == 'full_enumeration' else params['permutations']
    check('置换次数完整且符合既定规则', total == expected_total
          and (mode == 'full_enumeration') == (result['permutation']['n'] < params['full_enum_threshold']),
          f"{mode} {total} 次")
    check('冻结快照校验和一致', result['checksum'] == algo.checksum(snapshot))
    accounted = set(p['station'] for p in result['pairing']['pairs'])
    listed = set(x['station'] for x in result['pairing']['unmatched']) | set(x['station'] for x in result['pairing']['unzoned']) | set(x['station'] for x in result['pairing']['invalid'])
    check('配对与单独名单不重叠', not (accounted & listed))
    return {'passed': not failures, 'checks': checks, 'failures': failures,
            'summary': f'{len(checks)} 项核对，{len(failures)} 项未通过' if failures else f'{len(checks)} 项核对全部通过'}


def publish(db, user, id):
    s = db.get(RetestStudy, id)
    if not s:
        raise HTTPException(404, '未找到复测研究')
    if s.state == 'published':
        raise HTTPException(409, '该复测研究已经发布')
    if s.state != 'verified' or not s.result or not (s.verification or {}).get('passed'):
        raise HTTPException(409, '试算未齐全或核对未通过，暂不能发布')
    if len(s.progress.get('done', {})) != s.progress.get('batches'):
        raise HTTPException(409, '置换批次不完整，暂不能发布')
    s.state = 'published'; s.updated_at = now()
    log(db, user, 'retest.published', id, s.name)
    db.commit()
    return row(s)
