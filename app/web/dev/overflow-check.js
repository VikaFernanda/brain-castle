// Overflow check. Finds any icon (.i) or button whose box leaves its parent's box, plus buttons whose
// content is wider/taller than the button, plus a page that scrolls sideways. Logs each problem.
//
// Run it in Playwright on every screen:
//   page.add_script_tag(path="app/web/dev/overflow-check.js"); problems = page.evaluate("window.__overflowCheck()")
// or use app/web/dev/shoot.py, which does it for you. Empty list = clean.
(function () {
  var TOL = 0.75; // sub-pixel rounding
  function visible(el) {
    var r = el.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    var cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none';
  }
  function name(el) {
    var t = el.tagName.toLowerCase();
    if (el.id) t += '#' + el.id;
    var c = typeof el.className === 'string' ? el.className : (el.className && el.className.baseVal) || '';
    if (c) t += '.' + c.trim().split(/\s+/).join('.');
    var l = el.getAttribute('aria-label') || (el.textContent || '').trim().slice(0, 24);
    return t + (l ? ' [' + l + ']' : '');
  }
  function leaves(child, parent) {
    var a = child.getBoundingClientRect();
    var b = parent.getBoundingClientRect();
    return a.left < b.left - TOL || a.top < b.top - TOL || a.right > b.right + TOL || a.bottom > b.bottom + TOL;
  }
  window.__overflowCheck = function () {
    var problems = [];
    var els = document.querySelectorAll('.i, button');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (!visible(el)) continue;
      var parent = el.parentElement;
      if (parent && parent !== document.body && visible(parent) && leaves(el, parent)) {
        problems.push({ kind: 'leaves-parent', el: name(el), parent: name(parent) });
      }
      if (el.tagName === 'BUTTON' && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)) {
        problems.push({ kind: 'content-overflows-button', el: name(el) });
      }
    }
    var de = document.documentElement;
    if (de.scrollWidth > de.clientWidth + 1) problems.push({ kind: 'page-scrolls-sideways', el: 'html' });
    if (problems.length) console.log('OVERFLOW', JSON.stringify(problems, null, 2));
    return problems;
  };
})();
