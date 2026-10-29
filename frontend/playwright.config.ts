import {defineConfig,devices} from '@playwright/test';
import path from 'node:path';
const backend=path.resolve(import.meta.dirname,'../backend');
export default defineConfig({
 testDir:'./tests/e2e',fullyParallel:false,workers:1,timeout:45000,
 expect:{timeout:10000},reporter:[['list'],['html',{open:'never'}]],
 use:{baseURL:'http://127.0.0.1:5183',trace:'retain-on-failure',screenshot:'only-on-failure',...devices['Desktop Chrome']},
 webServer:[
  {command:`"${backend}/.venv/Scripts/python.exe" "${backend}/scripts/serve-e2e.py"`,url:'http://127.0.0.1:8011/api/ready',timeout:120000,reuseExistingServer:false},
  {command:'npm run dev -- --port 5183',url:'http://127.0.0.1:5183',env:{API_PROXY_TARGET:'http://127.0.0.1:8011'},timeout:60000,reuseExistingServer:false},
  {command:'npm run dev -- --port 5184',cwd:'../admin',url:'http://127.0.0.1:5184',env:{API_PROXY_TARGET:'http://127.0.0.1:8011'},timeout:60000,reuseExistingServer:false}
 ]
});
