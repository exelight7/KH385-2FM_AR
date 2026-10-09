const fs = require('node:fs/promises');
const path = require('node:path');
const {hash} = require('./core.cjs');
(async () => {
  const out = path.join(__dirname, '../out/apps');
  const version = require('./package.json').version;
  const windows = path.join(out, `Days-Arabic-Setup-${version}.exe`);
  if (await fs.access(windows).then(() => true, () => false)) {
    await fs.copyFile(windows, path.join(out, `Days-Arabic-Uninstall-${version}.exe`));
  }
  const files = (await fs.readdir(out)).filter(n => /\.(exe|AppImage)$/.test(n)).sort();
  const lines = [];
  for (const name of files) lines.push(`${await hash(path.join(out, name))}  ${name}`);
  await fs.writeFile(path.join(out, 'SHA256SUMS.txt'), lines.join('\n') + '\n');
  console.log(lines.join('\n'));
})().catch(e => { console.error(e); process.exitCode = 1; });
