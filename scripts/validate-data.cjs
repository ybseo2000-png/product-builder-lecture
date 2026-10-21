const fs = require('node:fs');
const path = require('node:path');
const { validateDataset } = require('../assets/data.js');
for (const kind of ['research', 'bids']) {
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', `${kind}.json`), 'utf8'));
  validateDataset(data, kind);
  console.log(`${kind}: ${data.status}, ${data.items.length} records; schema OK (not a source verification)`);
}
