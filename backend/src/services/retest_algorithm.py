"""复测配对与全区最大统计量校正。

纯计算模块：不连接数据库，输入冻结快照，输出可与快照独立复核的结果。
口径：
- 站号取样本编号末尾数字段（不含数字时用编号本身）；两期按站号一一配对，缺配/重复单独列出。
- 分区与标准化尺度沿用早期密度任务的冻结结果，不重新拟合。
- 每个分区取三项标准化平均变化的最大绝对值作为统计量。
- 置换时同站三项一起换期（等价于整站符号翻转），每次置换取全区最大统计量，
  以该最大值分布校正各区 p 值（Westfall–Young 式 max-statistic 校正）。
- 配对站数不足 10 时全枚举 2^n；否则固定种子 42 抽 10000 次。
"""
import hashlib
import json
import math
import re

import numpy as np

FEATURES = ['temperature', 'humidity', 'particles']
SEED = 42
PERMUTATIONS = 10000
FULL_ENUM_THRESHOLD = 10
ALPHA = 0.05
MIN_PAIRS = 1
BATCH_SIZE = 500


def station_key(reference):
    """站号：样本编号末尾的数字段，例如 HL-202611-01-0007 → 0007。

    编号完全不含数字时，以编号本身作为站号，只有两期编号完全一致才会配对。
    """
    if not isinstance(reference, str):
        return None
    text = reference.strip()
    if not text:
        return None
    match = re.search(r'(\d+)\s*$', text)
    return match.group(1) if match else text


def _values_by_reference(records):
    return {r['reference']: r for r in records}


def _index_period(records, label, conflicts):
    """按站号索引一期样本；同一站号出现多次时整站停用，并逐条留痕。"""
    seen = {}
    for record in records:
        key = station_key(record.get('reference'))
        if key is None:
            conflicts.append({'period': label, 'reference': record.get('reference'), 'reason': '样本编号无法解析站号'})
            continue
        seen.setdefault(key, []).append(record['reference'])
    indexed, duplicated = {}, set()
    for key, refs in seen.items():
        if len(refs) > 1:
            duplicated.add(key)
            for ref in refs:
                conflicts.append({'period': label, 'reference': ref, 'reason': '站号出现'+str(len(refs))+'次，无法唯一配对'})
        else:
            indexed[key] = refs[0]
    return indexed, duplicated


def _index_early(rows, conflicts):
    """按站号索引早期分区；同一站号出现多次时整站停用，并逐条留痕。"""
    seen = {}
    for row in rows:
        key = station_key(row.get('reference'))
        if key is None:
            conflicts.append({'period': 'early', 'reference': row.get('reference'), 'reason': '早期样本编号无法解析站号'})
            continue
        seen.setdefault(key, []).append(row)
    indexed, duplicated = {}, set()
    for key, group in seen.items():
        if len(group) > 1:
            duplicated.add(key)
            for row in group:
                conflicts.append({'period': 'early', 'reference': row['reference'], 'reason': '早期站号出现'+str(len(group))+'次，分区依据不唯一'})
        else:
            indexed[key] = group[0]
    return indexed, duplicated


def build_pairs(early_rows, period1_records, period2_records, scale):
    """按站号配对，返回配对行与各类单独名单。分区/尺度全部来自早期结果。"""
    conflicts = []
    early, early_dup = _index_early(early_rows, conflicts)
    first, dup1 = _index_period(period1_records, 'period1', conflicts)
    second, dup2 = _index_period(period2_records, 'period2', conflicts)
    values1 = _values_by_reference(period1_records)
    values2 = _values_by_reference(period2_records)
    conflicted = early_dup | dup1 | dup2

    pairs, unmatched, unzoned, invalid = [], [], [], []
    for key in sorted(set(early) | set(first) | set(second) | conflicted):
        if key in conflicted:
            continue
        ref1, ref2 = first.get(key), second.get(key)
        if not ref1 or not ref2:
            if ref1 and not ref2:
                reason = '仅第一期出现'
            elif ref2 and not ref1:
                reason = '仅第二期出现'
            else:
                reason = '两期均无该站样本（仅早期存在）'
            unmatched.append({'station': key, 'period1': ref1, 'period2': ref2, 'reason': reason})
            continue
        early_row = early.get(key)
        if early_row is None:
            unzoned.append({'station': key, 'reference': ref1, 'early_reference': None,
                            'reason': '早期任务无该站记录，沿用不到分区'})
            continue
        zone = int(early_row['cluster'])
        if zone < 0:
            unzoned.append({'station': key, 'reference': ref1, 'early_reference': early_row['reference'],
                            'reason': '早期为噪声站，无分区'})
            continue
        delta, delta_std = {}, {}
        bad = False
        for index, feature in enumerate(FEATURES):
            try:
                v1 = float(values1[ref1]['values'][feature])
                v2 = float(values2[ref2]['values'][feature])
            except (KeyError, TypeError, ValueError):
                bad = True
                break
            if not (math.isfinite(v1) and math.isfinite(v2)):
                bad = True
                break
            delta[feature] = v2 - v1
            delta_std[feature] = (v2 - v1) / float(scale[index])
        if bad:
            invalid.append({'station': key, 'reference1': ref1, 'reference2': ref2,
                            'early_reference': early_row['reference'],
                            'reason': '两期业务字段缺失或非有限数值'})
            continue
        pairs.append({'station': key, 'reference1': ref1, 'reference2': ref2,
                      'early_reference': early_row['reference'], 'zone': zone,
                      'delta': delta, 'delta_std': delta_std})
    return {'pairs': pairs, 'unmatched': unmatched, 'unzoned': unzoned,
            'conflicts': conflicts, 'invalid': invalid}


def early_zones(early_rows):
    """早期结果中出现过的全部分区（不含噪声），用于识别无配对站的分区。"""
    return sorted({int(r['cluster']) for r in early_rows if int(r['cluster']) >= 0})


def group_pairs(pairs, min_pairs=MIN_PAIRS, all_zones=None):
    """按早期分区归组；不足 min_pairs 的分区不参与检验，单独列出。"""
    groups = {}
    for index, pair in enumerate(pairs):
        groups.setdefault(pair['zone'], []).append(index)
    complete = set(groups) | set(all_zones or [])
    tested = sorted(g for g in complete if len(groups.get(g, [])) >= min_pairs)
    insufficient = [{'zone': g, 'n': len(groups.get(g, [])),
                     'stations': [pairs[i]['station'] for i in groups.get(g, [])]}
                    for g in sorted(complete) if g not in tested]
    order = [i for g in tested for i in groups[g]]
    zone_indices = {}
    position = 0
    for g in tested:
        zone_indices[g] = list(range(position, position + len(groups[g])))
        position += len(groups[g])
    deltas = np.array([[pairs[i]['delta_std'][f] for f in FEATURES] for i in order], float)
    return {'zones': tested, 'zone_indices': zone_indices, 'order': order,
            'deltas': deltas, 'insufficient': insufficient, 'n': len(order)}


def observed_statistics(pairs, grouped, scale):
    rows = []
    for zone in grouped['zones']:
        idx = grouped['zone_indices'][zone]
        means = {f: float(np.mean([pairs[grouped['order'][i]]['delta_std'][f] for i in idx])) for f in FEATURES}
        means_raw = {f: means[f] * float(scale[j]) for j, f in enumerate(FEATURES)}
        feature = max(FEATURES, key=lambda f: abs(means[f]))
        rows.append({'zone': zone, 'n': len(idx), 'means': means, 'means_raw': means_raw,
                     'max_abs': float(abs(means[feature])), 'max_feature': feature})
    return rows


def plan_permutations(n, seed=SEED, permutations=PERMUTATIONS, threshold=FULL_ENUM_THRESHOLD):
    if n < threshold:
        total = 2 ** n
        return {'mode': 'full_enumeration', 'n': n, 'total': total, 'batch_size': total,
                'batches': 1, 'seed': seed, 'threshold': threshold}
    return {'mode': 'monte_carlo', 'n': n, 'total': permutations, 'batch_size': BATCH_SIZE,
            'batches': int(math.ceil(permutations / BATCH_SIZE)), 'seed': seed, 'threshold': threshold}


def batch_signs(plan, batch_id):
    """同站三项一起换期：每个配对站得到一个 ±1，整站三项共用。"""
    n = plan['n']
    if plan['mode'] == 'full_enumeration':
        codes = np.arange(2 ** n)
        bits = (codes[:, None] >> np.arange(n)) & 1
        return np.where(bits == 1, 1.0, -1.0)
    remaining = plan['total'] - batch_id * plan['batch_size']
    size = min(plan['batch_size'], remaining)
    rng = np.random.default_rng(np.random.SeedSequence([plan['seed'], batch_id]))
    return rng.choice([-1.0, 1.0], size=(size, n))


def batch_exceedance(signs, deltas, zone_indices, thresholds):
    """每批置换的全区最大值 M_b，并按区统计 M_b ≥ T_zone 的次数。"""
    zone_max = np.empty((signs.shape[0], len(zone_indices)), float)
    for column, (zone, idx) in enumerate(zone_indices.items()):
        means = (signs[:, idx] @ deltas[idx]) / len(idx)
        zone_max[:, column] = np.abs(means).max(axis=1)
    overall = zone_max.max(axis=1)
    return {zone: int(np.sum(overall >= thresholds[zone] - 1e-12)) for zone in zone_indices}


def corrected_p(exceed, total, exact=False):
    """校正 p 值。

    全枚举：观测分配本身就在全部 2^n 个分配中，直接取超限比例。
    固定种子抽样：观测分配未必被抽到，按惯例加一校正 (1+超限)/(1+次数)。
    """
    if exact:
        return int(exceed) / float(total)
    return (1.0 + int(exceed)) / (1.0 + int(total))


def checksum(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
