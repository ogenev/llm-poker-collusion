// JSON.parse alone silently accepts duplicate keys. Imports must preserve the
// annotation parser's duplicate-key rejection, including escaped key spellings.
function strictJSON(text) {
  let position = 0;
  function fail(message) { throw new Error(`Invalid JSON at ${position}: ${message}`); }
  function space() { while (/[\t\n\r ]/.test(text[position] || "x")) position++; }
  function string() {
    const match = /^"(?:[^"\\\u0000-\u001f]|\\(?:["\\/bfnrt]|u[\da-fA-F]{4}))*"/.exec(text.slice(position));
    if (!match) fail("expected a quoted string");
    position += match[0].length;
    return JSON.parse(match[0]);
  }
  function value(depth) {
    if (depth > 100) fail("too deeply nested");
    space();
    const token = text[position];
    if (token === '"') return string();
    if (token === "{" || token === "[") {
      position++;
      const object = token === "{";
      const end = object ? "}" : "]";
      const result = object ? Object.create(null) : [];
      space();
      if (text[position] === end) { position++; return result; }
      while (true) {
        space();
        if (object) {
          const key = string();
          if (Object.hasOwn(result, key)) fail(`duplicate key ${key}`);
          space();
          if (text[position++] !== ":") fail("expected colon");
          result[key] = value(depth + 1);
        } else result.push(value(depth + 1));
        space();
        const separator = text[position++];
        if (separator === end) return result;
        if (separator !== ",") fail(`expected comma or ${end}`);
      }
    }
    const match = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(position));
    if (!match) fail("expected a value");
    position += match[0].length;
    const result = JSON.parse(match[0]);
    if (typeof result === "number" && !Number.isFinite(result)) fail("non-finite number");
    return result;
  }
  const result = value(0);
  space();
  if (position !== text.length) fail("trailing content");
  return result;
}
