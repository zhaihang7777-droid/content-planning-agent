"""Run real gateway decisions against synthetic tools; never save credentials."""
import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from content_agent.agent import Agent
from content_agent.tools import Tools
from content_agent.gemini_model import GeminiModel
ROOT = Path(__file__).resolve().parents[1]
for name, budget, fail in [('normal',20,[]), ('budget',10,[]), ('failure',20,['generate_script_standard']), ('time_short',20,[])]:
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        continue
    with tempfile.TemporaryDirectory() as directory:
        tools=Tools(ROOT,Path(directory)/'db',fail)
        try:
            request={'request_id':'real-'+name,'theme':'字幕','budget':budget,'deadline':'2030-01-01T00:00:00+00:00'}
            started = datetime.now(timezone.utc)
            if name == 'time_short':
                request['deadline'] = (started + timedelta(seconds=50)).isoformat()
            result=Agent(tools,GeminiModel(), clock=lambda: started).run(request)
            (ROOT/'examples/real'/f'{name}.json').write_text(json.dumps({'input':request,'fail_once':fail,'clock':started.isoformat(),'model':'gemini-2.5-flash','output':result},ensure_ascii=False,indent=2)+'\n')
            print(name,result['status'],result['reason'],flush=True)
        finally:
            tools.close()
