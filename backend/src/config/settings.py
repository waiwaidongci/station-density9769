import json, os
from pathlib import Path
CONFIG=json.loads((Path(__file__).parent / 'domain.json').read_text())
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./dev.db')
REDIS_URL=os.getenv('REDIS_URL','redis://localhost:6379/0')
JWT_SECRET=os.getenv('JWT_SECRET','local-only-change-before-deployment')
ARTIFACT_DIR=Path(os.getenv('ARTIFACT_DIR','/artifacts'))
