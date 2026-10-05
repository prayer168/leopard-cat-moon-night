var html = require('fs').readFileSync('game.html','utf8');
var re = /<script(?! src)[^>]*>([\s\S]*?)<\/script>/g, m, n=0;
while ((m = re.exec(html))) { n++;
  try { new Function(m[1]); console.log('JS OK'); } catch(e) { console.log('ERROR:', e.message); }
  var bad = m[1].match(/[−—–·✓‘’“”→★…`]|=>/g);
  console.log('special chars:', bad ? bad.join(' ') : 'none');
}
