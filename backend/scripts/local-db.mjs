import EmbeddedPostgres from '../tools/node_modules/embedded-postgres/dist/index.js';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { randomBytes } from 'node:crypto';

const root=resolve(import.meta.dirname,'..');
const local=resolve(root,'.local');
mkdirSync(local,{recursive:true});
const passwordFile=resolve(local,'postgres-password');
const password=existsSync(passwordFile)?readFileSync(passwordFile,'utf8'):randomBytes(24).toString('hex');
if(!existsSync(passwordFile))writeFileSync(passwordFile,password,{mode:0o600});
const directory=resolve(local,'postgres');
const pg=new EmbeddedPostgres({databaseDir:directory,user:'tura_dev',password,port:55432,persistent:true,authMethod:'scram-sha-256',postgresFlags:['-h','127.0.0.1'],onLog:()=>{},onError:()=>{}});
if(!existsSync(resolve(directory,'PG_VERSION')))await pg.initialise();
await pg.start();
const client=pg.getPgClient();await client.connect();
const databases=['tura_dev','tura_test'];
for(const name of databases){
  const result=await client.query('SELECT 1 FROM pg_database WHERE datname=$1',[name]);
  if(!result.rowCount)await client.query(`CREATE DATABASE ${name}`);
}
await client.end();
writeFileSync(resolve(local,'database.json'),JSON.stringify({development:`postgresql+psycopg://tura_dev:${password}@127.0.0.1:55432/tura_dev`,test:`postgresql+psycopg://tura_dev:${password}@127.0.0.1:55432/tura_test`}),{mode:0o600});
console.log('Local PostgreSQL ready on 127.0.0.1:55432. Separate development and test databases are available.');
console.log('Supabase settings have not been changed. Press Ctrl+C to stop.');
let stopping=false;
async function stop(){if(stopping)return;stopping=true;await pg.stop();process.exit(0);}
process.on('SIGINT',stop);process.on('SIGTERM',stop);
setInterval(()=>{},60000);
