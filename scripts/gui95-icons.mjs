// This file is copied verbatim into each GUI95 app as scripts/gui95-icons.mjs, so every
// copy must stay byte-identical and dependency-free: Node >= 20.11, built-in modules only.
//
// It makes an app's icons from its SVG sources, with no browser. The `icons` array of
// gui95-app.json lists them:
//   { "name": "app", "svg": "art/icon.svg", "style": "pixel" }
//   { "name": "file", "svg": "art/icon.svg", "style": "pixel", "document": true, "master": 64 }
//   { "name": "logo", "svg": "art/logo.svg", "style": "smooth" }
// Run from the repository root,
//   node scripts/gui95-icons.mjs
// writes gui95-icons/<name>.png (1024 px), <name>.ico and <name>.icns for each one.
//
// Styles:
//   pixel   draws 16, 24, 32, 48 px and `master` px (default 32; 16, 32, 64, ... 1024) directly,
//           each pixel taking the colour that covers most of it (translucent paints are blended
//           with what is below them first, as in smooth), and enlarges that `master` drawing by
//           whole numbers for every larger size, so the hard-edged look survives at 1024 px.
//   smooth  draws every size directly, antialiased by supersampling (8 x 8 samples per pixel up
//           to 256 px, 4 x 4 above), the samples' colours averaged with their alpha.
// `document: true` puts the picture at half size on a Windows 95 document page. With a pixel
// style, give such an icon a `master` of twice the plain icon's to keep the plain icon's pixels.
//
// The SVG may use: the root <svg> with a viewBox; <g>; <path> (M L H V C S Q T Z, absolute and
// relative); <rect> (no rounded corners); <circle>; <ellipse>; <polygon>; transform (translate,
// scale, matrix); fill, fill-rule, fill-opacity, opacity, stroke, stroke-width, stroke-linejoin
// (miter, round or bevel), stroke-miterlimit and display (none or inline); colours #rgb, #rrggbb,
// none, black and white. Fill, fill-rule, fill-opacity, stroke, stroke-width, stroke-linejoin and
// stroke-miterlimit are inherited as in SVG.
// <metadata>, <title> and <desc> are skipped, and so are comments and attributes that only
// label or size the picture (id, class, data-*, width and height of the root, ...). Anything
// else is refused with an error naming it, so a feature the icons cannot show never drops out
// silently. Two simplifications: strokes have plain (butt) ends, and a stroke's width scales with
// the square root of the transform's area scale. Joins are as in SVG: miter by default, with a
// miter limit of 4. An element's opacity applies to it and its content as a whole.

import { realpathSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

export const ICON_DIR = "gui95-icons";

const MANIFEST = "gui95-app.json";
const STYLES = ["pixel", "smooth"];
const MASTERS = [16, 32, 64, 128, 256, 512, 1024];   // whole-number factors reach every larger icon size
const DRAWN_SIZES = [16, 24, 32, 48];                // the sizes the pixel style always draws directly
const PNG_SIZE = 1024;
const ICO_SIZES = [16, 24, 32, 48, 64, 128, 256];
// [type, pixels, format]: what iconutil writes for a full .iconset.
const ICNS_ENTRIES = [
  ["ic04", 16, "argb"],
  ["ic05", 32, "argb"],
  ["ic11", 32, "png"],
  ["ic12", 64, "png"],
  ["ic07", 128, "png"],
  ["ic13", 256, "png"],
  ["ic08", 256, "png"],
  ["ic14", 512, "png"],
  ["ic09", 512, "png"],
  ["ic10", 1024, "png"],
];
const MAX_SIZE = 4096;

// ---- The icons listed in gui95-app.json -----------------------------------------

const isObject = (value) => typeof value === "object" && value !== null && !Array.isArray(value);

function invalid(field, problem) {
  return new Error(`${MANIFEST}: ${field} ${problem}`);
}

export async function readIconList(repoRoot) {
  let manifest;
  try {
    manifest = JSON.parse((await readFile(path.join(repoRoot, MANIFEST), "utf8")).replace(/^\uFEFF/, ""));
  } catch (err) {
    throw new Error(`${MANIFEST}: cannot read it from ${repoRoot} (${err.message})`, { cause: err });
  }
  if (!isObject(manifest)) throw invalid("the top level", "must be an object");
  if (manifest.icons === undefined) return [];
  if (!Array.isArray(manifest.icons)) throw invalid("icons", "must be an array");

  const names = new Map();
  manifest.icons.forEach((icon, index) => {
    const field = `icons[${index}]`;
    if (!isObject(icon)) throw invalid(field, "must be an object");
    if (typeof icon.name !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(icon.name)) {
      throw invalid(`${field}.name`, "must use lowercase letters, digits and hyphens, and start with a letter or digit");
    }
    if (names.has(icon.name)) throw invalid(`${field}.name`, `"${icon.name}" is already the name of icons[${names.get(icon.name)}]`);
    names.set(icon.name, index);
    if (typeof icon.svg !== "string" || icon.svg.trim() === "" || /^([a-z]:|[\\/])/i.test(icon.svg) || icon.svg.split(/[\\/]/).includes("..")) {
      throw invalid(`${field}.svg`, "must be the path of an SVG file inside the repository, relative to it");
    }
    if (!STYLES.includes(icon.style)) throw invalid(`${field}.style`, `must be one of ${STYLES.join(", ")}`);
    if (icon.document !== undefined && typeof icon.document !== "boolean") throw invalid(`${field}.document`, "must be true or false");
    if (icon.master !== undefined) {
      if (icon.style !== "pixel") throw invalid(`${field}.master`, "only applies to the pixel style");
      if (!MASTERS.includes(icon.master)) throw invalid(`${field}.master`, `must be one of ${MASTERS.join(", ")}`);
    }
  });
  return manifest.icons.map((icon) => ({ ...icon }));
}

// ---- Reading SVG -------------------------------------------------------------------

const NUMBER = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/;

function toNumber(text) {
  const value = NUMBER.test(text) ? Number(text) : NaN;
  return Number.isFinite(value) ? value : NaN;
}

function numberAttribute(attributes, name, fallback = 0) {
  if (attributes[name] === undefined) return fallback;
  const value = toNumber(attributes[name].trim());
  if (Number.isNaN(value)) throw new Error(`Invalid ${name} "${attributes[name]}": expected a plain number, without units`);
  return value;
}

function decodeEntities(text) {
  const named = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
  return text.replace(/&(?:#x([\da-f]+)|#(\d+)|(\w+));/gi, (whole, hex, decimal, name) => {
    if (name !== undefined) return Object.hasOwn(named, name) ? named[name] : whole;
    const code = hex !== undefined ? parseInt(hex, 16) : Number(decimal);
    return code <= 0x10ffff ? String.fromCodePoint(code) : whole;
  });
}

// The tags of an XML text, in order: { closing, name, attributes, selfClosing, start, end }.
// Comments, processing instructions, CDATA and the DOCTYPE are skipped; text between tags is not
// reported.
function* markup(text) {
  const malformed = (what) => new Error(`The SVG is not well-formed XML: ${what}`);
  const attribute = /([^\s=/>]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/y;
  const blanks = /\s*/y;
  const word = /[^\s/>]+/y;
  const endOf = (terminator, from) => {
    const end = text.indexOf(terminator, from);
    if (end < 0) throw malformed(`"${terminator}" is missing`);
    return end + terminator.length;
  };
  let at = 0;
  for (;;) {
    at = text.indexOf("<", at);
    if (at < 0) return;
    if (text.startsWith("<!--", at)) at = endOf("-->", at + 4);
    else if (text.startsWith("<![CDATA[", at)) at = endOf("]]>", at + 9);
    else if (text.startsWith("<?", at)) at = endOf("?>", at + 2);
    else if (text.startsWith("<!", at)) {
      let depth = 0; // A DOCTYPE may hold a [ ... ] subset with > inside.
      let i = at + 2;
      while (i < text.length && !(text[i] === ">" && depth <= 0)) depth += text[i] === "[" ? 1 : text[i] === "]" ? -1 : 0, i++;
      if (i >= text.length) throw malformed("a declaration is never closed");
      at = i + 1;
    } else {
      const start = at;
      const closing = text[at + 1] === "/";
      word.lastIndex = at + (closing ? 2 : 1);
      const name = word.exec(text)?.[0];
      if (name === undefined) throw malformed(`a tag without a name at "${text.slice(at, at + 20)}"`);
      at = word.lastIndex;
      const attributes = {};
      let selfClosing = false;
      for (;;) {
        blanks.lastIndex = at;
        blanks.exec(text);
        at = blanks.lastIndex;
        if (at >= text.length) throw malformed(`<${name}> is never finished`);
        if (text[at] === ">") {
          at++;
          break;
        }
        if (text[at] === "/" && text[at + 1] === ">") {
          selfClosing = true;
          at += 2;
          break;
        }
        attribute.lastIndex = at;
        const match = attribute.exec(text);
        if (!match) throw malformed(`<${name}> has something that is not name="value" at "${text.slice(at, at + 20)}"`);
        attributes[match[1]] = decodeEntities(match[2] ?? match[3]);
        at = attribute.lastIndex;
      }
      yield { closing, name, attributes, selfClosing, start, end: at };
    }
  }
}

const IDENTITY = [1, 0, 0, 1, 0, 0];

// The matrix of `outer` applied after `inner`; [a, b, c, d, e, f] maps (x, y) to (a x + c y + e, b x + d y + f).
function multiply(outer, inner) {
  const [a, b, c, d, e, f] = outer;
  const [a2, b2, c2, d2, e2, f2] = inner;
  return [a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2, a * e2 + c * f2 + e, b * e2 + d * f2 + f];
}

function parseTransform(text) {
  const call = /\s*([A-Za-z]+)\s*\(([^()]*)\)\s*,?\s*/y;
  const source = text.trim();
  let matrix = IDENTITY;
  while (call.lastIndex < source.length) {
    const match = call.exec(source);
    if (!match) throw new Error(`Cannot read the transform "${text}"`);
    const [, name, list] = match;
    const args = list.trim() === "" ? [] : list.trim().split(/[\s,]+/).map(toNumber);
    if (args.some(Number.isNaN)) throw new Error(`Cannot read the numbers of the transform "${text}"`);
    const count = (...allowed) => {
      if (!allowed.includes(args.length)) throw new Error(`${name}() in the transform "${text}" needs ${allowed.join(" or ")} numbers`);
    };
    if (name === "translate") {
      count(1, 2);
      matrix = multiply(matrix, [1, 0, 0, 1, args[0], args[1] ?? 0]);
    } else if (name === "scale") {
      count(1, 2);
      matrix = multiply(matrix, [args[0], 0, 0, args[1] ?? args[0], 0, 0]);
    } else if (name === "matrix") {
      count(6);
      matrix = multiply(matrix, args);
    } else {
      throw new Error(`Unsupported transform ${name}() in "${text}": only translate, scale and matrix work`);
    }
  }
  return matrix;
}

function parseColor(value, attribute) {
  const text = value.trim().toLowerCase();
  if (text === "none") return null;
  if (text === "black") return [0, 0, 0];
  if (text === "white") return [255, 255, 255];
  const hex = /^#([\da-f]{3}|[\da-f]{6})$/.exec(text)?.[1];
  if (!hex) throw new Error(`Unsupported ${attribute} "${value}": the colours are #rgb, #rrggbb, none, black and white`);
  const full = hex.length === 3 ? [...hex].map((digit) => digit + digit).join("") : hex;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
}

function parseOpacity(value, attribute) {
  const number = toNumber(value.trim());
  if (!(number >= 0 && number <= 1)) throw new Error(`Invalid ${attribute} "${value}": expected a number from 0 to 1`);
  return number;
}

// A path is a list of subpaths { start: [x, y], segments, closed }; a segment is [x, y] for a line
// or [x1, y1, x2, y2, x, y] for a cubic curve (quadratics are raised to cubics).
const ARITY = { M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, Z: 0 };

function parsePath(d) {
  const subpaths = [];
  const token = /([A-Za-z])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|[\s,]+|([^])/gy;
  let current = null;
  let x = 0;
  let y = 0;
  let startX = 0;
  let startY = 0;
  let cubicControl = null; // The second control point of a cubic just drawn, for S.
  let quadControl = null; // The control point of a quadratic just drawn, for T.

  const draw = (letter, n) => {
    const relative = letter !== letter.toUpperCase();
    const command = letter.toUpperCase();
    const ox = relative ? x : 0;
    const oy = relative ? y : 0;
    let nextCubic = null;
    let nextQuad = null;
    if (command !== "M" && command !== "Z" && current.closed) {
      current = { start: [x, y], segments: [], closed: false };
      subpaths.push(current);
    }
    const cubic = (x1, y1, x2, y2, x3, y3) => {
      current.segments.push([x1, y1, x2, y2, x3, y3]);
      nextCubic = [x2, y2];
      [x, y] = [x3, y3];
    };
    switch (command) {
      case "M":
        [x, y] = [ox + n[0], oy + n[1]];
        [startX, startY] = [x, y];
        current = { start: [x, y], segments: [], closed: false };
        subpaths.push(current);
        break;
      case "L":
        [x, y] = [ox + n[0], oy + n[1]];
        current.segments.push([x, y]);
        break;
      case "H":
        x = ox + n[0];
        current.segments.push([x, y]);
        break;
      case "V":
        y = oy + n[0];
        current.segments.push([x, y]);
        break;
      case "C":
        cubic(ox + n[0], oy + n[1], ox + n[2], oy + n[3], ox + n[4], oy + n[5]);
        break;
      case "S": {
        const [c1x, c1y] = cubicControl ? [2 * x - cubicControl[0], 2 * y - cubicControl[1]] : [x, y];
        cubic(c1x, c1y, ox + n[0], oy + n[1], ox + n[2], oy + n[3]);
        break;
      }
      case "Q":
      case "T": {
        const [qx, qy] = command === "Q" ? [ox + n[0], oy + n[1]] : quadControl ? [2 * x - quadControl[0], 2 * y - quadControl[1]] : [x, y];
        const [ex, ey] = command === "Q" ? [ox + n[2], oy + n[3]] : [ox + n[0], oy + n[1]];
        cubic(x + (2 / 3) * (qx - x), y + (2 / 3) * (qy - y), ex + (2 / 3) * (qx - ex), ey + (2 / 3) * (qy - ey), ex, ey);
        nextCubic = null; // S only continues a cubic that was drawn as one.
        nextQuad = [qx, qy];
        break;
      }
      case "Z":
        current.closed = true;
        [x, y] = [startX, startY];
        break;
    }
    cubicControl = nextCubic;
    quadControl = nextQuad;
  };

  let letter = null; // The command in force, and the numbers gathered for its next group.
  let numbers = [];
  let groups = 0;
  let first = true;
  const finishCommand = () => {
    if (letter !== null && ARITY[letter.toUpperCase()] > 0 && (numbers.length > 0 || groups === 0)) {
      throw new Error(`Path command ${letter} needs ${ARITY[letter.toUpperCase()]} numbers each time`);
    }
  };
  for (let match; (match = token.exec(d)); ) {
    if (match[3] !== undefined) throw new Error(`Cannot read the path data "${d.length > 40 ? `${d.slice(0, 40)}...` : d}": unexpected "${match[3]}"`);
    if (match[1] !== undefined) {
      finishCommand();
      letter = match[1];
      const command = letter.toUpperCase();
      if (!Object.hasOwn(ARITY, command)) throw new Error(`Unsupported path command ${letter}`);
      if (first && command !== "M") throw new Error("Path data must start with M");
      first = false;
      numbers = [];
      groups = 0;
      if (command === "Z") {
        draw(letter, numbers);
        groups = 1;
      }
    } else if (match[2] !== undefined) {
      if (first) throw new Error("Path data must start with M");
      const command = letter.toUpperCase();
      if (command === "Z") throw new Error(`Path command ${letter} takes no number, but "${match[2]}" follows it`);
      const value = toNumber(match[2]);
      if (Number.isNaN(value)) throw new Error(`Path number "${match[2]}" is too large`);
      numbers.push(value);
      if (numbers.length === ARITY[command]) {
        draw(letter, numbers);
        numbers = [];
        groups++;
        if (command === "M") letter = letter === "m" ? "l" : "L"; // Further pairs after a move are lines.
      }
    }
  }
  finishCommand();
  return subpaths;
}

const KAPPA = 0.5522847498307936; // The control point distance that makes four cubics a circle.

function ellipseSubpath(cx, cy, rx, ry) {
  const kx = KAPPA * rx;
  const ky = KAPPA * ry;
  return {
    start: [cx + rx, cy],
    segments: [
      [cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry],
      [cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy],
      [cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry],
      [cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy],
    ],
    closed: true,
  };
}

function shapeGeometry(element, attributes) {
  if (element === "path") return attributes.d === undefined ? [] : parsePath(attributes.d);
  if (element === "rect") {
    const [x, y, width, height] = ["x", "y", "width", "height"].map((name) => numberAttribute(attributes, name));
    if (!(width > 0 && height > 0)) return [];
    return [{ start: [x, y], segments: [[x + width, y], [x + width, y + height], [x, y + height]], closed: true }];
  }
  if (element === "circle") {
    const r = numberAttribute(attributes, "r");
    return r > 0 ? [ellipseSubpath(numberAttribute(attributes, "cx"), numberAttribute(attributes, "cy"), r, r)] : [];
  }
  if (element === "ellipse") {
    const [rx, ry] = [numberAttribute(attributes, "rx"), numberAttribute(attributes, "ry")];
    return rx > 0 && ry > 0 ? [ellipseSubpath(numberAttribute(attributes, "cx"), numberAttribute(attributes, "cy"), rx, ry)] : [];
  }
  if (element === "polygon") {
    const text = (attributes.points ?? "").trim();
    const numbers = text === "" ? [] : text.split(/[\s,]+/).map(toNumber);
    if (numbers.some(Number.isNaN) || numbers.length % 2 === 1) throw new Error(`Invalid points "${attributes.points}": expected pairs of plain numbers`);
    if (numbers.length < 4) return [];
    const segments = [];
    for (let i = 2; i < numbers.length; i += 2) segments.push([numbers[i], numbers[i + 1]]);
    return [{ start: [numbers[0], numbers[1]], segments, closed: true }];
  }
  return [];
}

const PRESENTATION = ["fill", "fill-rule", "fill-opacity", "opacity", "stroke", "stroke-width", "stroke-linejoin", "stroke-miterlimit", "display"];
const GEOMETRY = {
  svg: ["viewBox", "width", "height"],
  g: ["transform"],
  path: ["transform", "d"],
  rect: ["transform", "x", "y", "width", "height"],
  circle: ["transform", "cx", "cy", "r"],
  ellipse: ["transform", "cx", "cy", "rx", "ry"],
  polygon: ["transform", "points"],
};
const SKIPPED = ["metadata", "title", "desc"];
// Attributes that label the picture or tell a viewer how to size it, but change nothing drawn here.
const HARMLESS = /^(?:id|class|version|role|shape-rendering|xmlns(?::.+)?|xml:.+|data-.+|aria-.+)$/;

function parseViewBox(attributes) {
  const box = (attributes.viewBox ?? "").trim().split(/[\s,]+/).map(toNumber);
  if (box.length !== 4 || box.some(Number.isNaN) || !(box[2] > 0 && box[3] > 0)) {
    throw new Error("The SVG needs a viewBox of four numbers (min-x min-y width height) with a positive width and height");
  }
  return box;
}

// The state a child inherits from its parent plus the presentation attributes it sets itself.
function inherit(parent, attributes) {
  const state = { ...parent };
  if (attributes.fill !== undefined) state.fill = parseColor(attributes.fill, "fill");
  if (attributes.stroke !== undefined) state.stroke = parseColor(attributes.stroke, "stroke");
  if (attributes["fill-opacity"] !== undefined) state.fillOpacity = parseOpacity(attributes["fill-opacity"], "fill-opacity");
  if (attributes["fill-rule"] !== undefined) {
    const rule = attributes["fill-rule"].trim();
    if (rule !== "nonzero" && rule !== "evenodd") throw new Error(`Unsupported fill-rule "${attributes["fill-rule"]}": use nonzero or evenodd`);
    state.evenOdd = rule === "evenodd";
  }
  if (attributes["stroke-width"] !== undefined) {
    state.strokeWidth = numberAttribute(attributes, "stroke-width");
    if (state.strokeWidth < 0) throw new Error(`Invalid stroke-width "${attributes["stroke-width"]}": it cannot be negative`);
  }
  if (attributes["stroke-linejoin"] !== undefined) {
    const join = attributes["stroke-linejoin"].trim();
    if (join !== "miter" && join !== "round" && join !== "bevel") {
      throw new Error(`Unsupported stroke-linejoin "${attributes["stroke-linejoin"]}": use miter, round or bevel`);
    }
    state.join = join;
  }
  if (attributes["stroke-miterlimit"] !== undefined) {
    state.miterLimit = numberAttribute(attributes, "stroke-miterlimit");
    if (state.miterLimit < 1) throw new Error(`Invalid stroke-miterlimit "${attributes["stroke-miterlimit"]}": it must be at least 1`);
  }
  if (attributes.transform !== undefined) state.matrix = multiply(parent.matrix, parseTransform(attributes.transform));
  return state;
}

// Reads SVG into { viewBox, items }: the shapes in painting order, each with its subpaths, matrix and paints.
// An element whose opacity is below 1 is drawn as one: its content goes into a group { opacity, items }.
function readSvg(text) {
  const items = [];
  const stack = []; // The open elements: { name, state, items }, items being where the element's content goes.
  let viewBox = null;
  let skipping = 0; // How deep inside an element that is not drawn.
  for (const tag of markup(text)) {
    if (skipping > 0) {
      skipping += tag.closing ? -1 : tag.selfClosing ? 0 : 1;
      continue;
    }
    if (tag.closing) {
      if (stack.pop()?.name !== tag.name) throw new Error(`The SVG is not well-formed XML: </${tag.name}> closes nothing that is open`);
      continue;
    }
    const { name, attributes } = tag;
    if (stack.length === 0) {
      if (viewBox !== null) throw new Error(`Unsupported content after the root <svg>: <${name}>`);
      if (name !== "svg") throw new Error(`The SVG needs a root <svg> element, not <${name}>`);
    } else if (name === "svg") {
      throw new Error("Unsupported element <svg>: only the root can be an <svg>");
    }
    if (SKIPPED.includes(name)) {
      if (!tag.selfClosing) skipping = 1;
      continue;
    }
    if (!Object.hasOwn(GEOMETRY, name)) throw new Error(`Unsupported element <${name}>`);
    const allowed = [...PRESENTATION, ...GEOMETRY[name]];
    for (const attribute of Object.keys(attributes)) {
      if (!allowed.includes(attribute) && !HARMLESS.test(attribute)) throw new Error(`Unsupported attribute ${attribute} on <${name}>`);
    }
    if (name === "svg") viewBox = parseViewBox(attributes);
    const parent = stack.at(-1)?.state ?? { fill: [0, 0, 0], fillOpacity: 1, evenOdd: false, stroke: null, strokeWidth: 1, join: "miter", miterLimit: 4, matrix: IDENTITY };
    const state = inherit(parent, attributes);
    const opacity = attributes.opacity === undefined ? 1 : parseOpacity(attributes.opacity, "opacity");
    const display = attributes.display?.trim();
    if (display !== undefined && display !== "none" && display !== "inline") throw new Error(`Unsupported display "${attributes.display}": use none or inline`);
    if (display === "none" || opacity === 0) {
      if (!tag.selfClosing) skipping = 1;
      continue;
    }
    let content = stack.at(-1)?.items ?? items;
    if (opacity < 1) {
      const group = { opacity, items: [] };
      content.push(group);
      content = group.items;
    }
    const subpaths = shapeGeometry(name, attributes);
    if (subpaths.length > 0) {
      content.push({
        subpaths,
        matrix: state.matrix,
        fill: state.fill,
        fillAlpha: state.fillOpacity,
        evenOdd: state.evenOdd,
        stroke: state.stroke,
        strokeWidth: state.strokeWidth,
        join: state.join,
        miterLimit: state.miterLimit,
      });
    }
    if (!tag.selfClosing) stack.push({ name, state, items: content });
  }
  if (viewBox === null) throw new Error("The SVG needs a root <svg> element");
  if (stack.length > 0) throw new Error(`The SVG is not well-formed XML: <${stack.at(-1).name}> is never closed`);
  return { viewBox, items };
}

// ---- Drawing ------------------------------------------------------------------------

const FLATNESS = 0.05; // How far, in output pixels, a flattened curve or a round join may stray.

// A subpath in output pixels, curves flattened: { points: [x0, y0, x1, y1, ...], closed }.
function flatten({ start, segments, closed }, m) {
  const place = (x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  const points = place(start[0], start[1]);
  for (const segment of segments) {
    const [x0, y0] = [points.at(-2), points.at(-1)];
    if (segment.length === 2) {
      points.push(...place(segment[0], segment[1]));
      continue;
    }
    const [x1, y1] = place(segment[0], segment[1]);
    const [x2, y2] = place(segment[2], segment[3]);
    const [x3, y3] = place(segment[4], segment[5]);
    // A cubic strays at most 0.75 * dd / n^2 from n straight pieces, dd being its largest second difference.
    const dd = Math.max(Math.hypot(x0 - 2 * x1 + x2, y0 - 2 * y1 + y2), Math.hypot(x1 - 2 * x2 + x3, y1 - 2 * y2 + y3));
    const n = Math.min(1000, Math.max(1, Math.ceil(Math.sqrt((0.75 * dd) / FLATNESS)) || 1));
    for (let i = 1; i <= n; i++) {
      const t = i / n;
      const u = 1 - t;
      const [a, b, c, d] = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t];
      points.push(a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3);
    }
  }
  return { points, closed };
}

// Edges for the scanline fill, as parallel arrays: the top and bottom y, x at the top, dx/dy and the direction.
function newEdges() {
  return { top: [], bottom: [], x: [], slope: [], direction: [] };
}

function addEdge(edges, x0, y0, x1, y1) {
  if (y0 === y1 || !Number.isFinite(x0 + y0 + x1 + y1)) return;
  const down = y0 < y1;
  edges.top.push(down ? y0 : y1);
  edges.bottom.push(down ? y1 : y0);
  edges.x.push(down ? x0 : x1);
  edges.slope.push((x1 - x0) / (y1 - y0));
  edges.direction.push(down ? 1 : -1);
}

function addPolygon(edges, points, reverseIfNegative = false) {
  const count = points.length;
  if (reverseIfNegative) {
    let area = 0;
    for (let i = 0; i < count; i += 2) area += points[i] * points[(i + 3) % count] - points[(i + 2) % count] * points[i + 1];
    if (area === 0) return;
    if (area < 0) {
      const flipped = [];
      for (let i = count - 2; i >= 0; i -= 2) flipped.push(points[i], points[i + 1]);
      points = flipped;
    }
  }
  for (let i = 0; i < count; i += 2) addEdge(edges, points[i], points[i + 1], points[(i + 2) % count], points[(i + 3) % count]);
}

// A stroke as the union of convex pieces, all wound the same way so that a nonzero fill merges them: a
// rectangle along each line, and a wedge on the outside of each bend, shaped by the join: a miter
// (the outer edges extended to a point, unless that point is more than `miterLimit` stroke widths
// from the bend, when it is cut off as a bevel), a bevel (a triangle) or a round one (a pie slice).
// The ends of open lines are flat.
function addStroke(edges, { points, closed }, halfWidth, join, miterLimit) {
  const p = [];
  for (let i = 0; i < points.length; i += 2) {
    if (p.length === 0 || Math.hypot(points[i] - p.at(-2), points[i + 1] - p.at(-1)) > 1e-9) p.push(points[i], points[i + 1]);
  }
  if (closed && p.length > 2 && Math.hypot(p[0] - p.at(-2), p[1] - p.at(-1)) <= 1e-9) p.length -= 2;
  const count = p.length / 2;
  if (count < 2) return;
  const direction = (i) => {
    const [x0, y0, x1, y1] = [p[2 * i], p[2 * i + 1], p[2 * ((i + 1) % count)], p[2 * ((i + 1) % count) + 1]];
    const length = Math.hypot(x1 - x0, y1 - y0);
    return [(x1 - x0) / length, (y1 - y0) / length];
  };
  const step = FLATNESS >= halfWidth ? Math.PI : 2 * Math.acos(1 - FLATNESS / halfWidth);
  const lines = closed ? count : count - 1;
  for (let i = 0; i < lines; i++) {
    const [dx, dy] = direction(i);
    const [nx, ny] = [-dy * halfWidth, dx * halfWidth];
    const [x0, y0, x1, y1] = [p[2 * i], p[2 * i + 1], p[2 * ((i + 1) % count)], p[2 * ((i + 1) % count) + 1]];
    addPolygon(edges, [x0 + nx, y0 + ny, x1 + nx, y1 + ny, x1 - nx, y1 - ny, x0 - nx, y0 - ny], true);
  }
  for (let i = closed ? 0 : 1; i < (closed ? count : count - 1); i++) {
    const [d1x, d1y] = direction((i + count - 1) % count);
    const [d2x, d2y] = direction(i);
    const [vx, vy] = [p[2 * i], p[2 * i + 1]];
    const turn = Math.atan2(d1x * d2y - d1y * d2x, d1x * d2x + d1y * d2y);
    if (Math.abs(turn) < 1e-6) continue;
    const wedge = [];
    if (Math.abs(turn) > Math.PI - 1e-3) {
      // A line that turns back on itself: a round join is a whole circle, the others end flat.
      if (join !== "round") continue;
      const corners = Math.max(8, Math.ceil((2 * Math.PI) / step));
      for (let k = 0; k < corners; k++) {
        const angle = (2 * Math.PI * k) / corners;
        wedge.push(vx + halfWidth * Math.cos(angle), vy + halfWidth * Math.sin(angle));
      }
    } else {
      // The outside of the bend is away from the side it turns toward.
      wedge.push(vx, vy);
      const side = turn > 0 ? -1 : 1;
      const [ax, ay] = [-d1y * halfWidth * side, d1x * halfWidth * side]; // The outer corner of the first line,
      const [bx, by] = [-d2y * halfWidth * side, d2x * halfWidth * side]; // and of the second.
      if (join === "round") {
        const pieces = Math.ceil(Math.abs(turn) / step);
        for (let k = 0; k <= pieces; k++) {
          const angle = (turn * k) / pieces;
          wedge.push(vx + ax * Math.cos(angle) - ay * Math.sin(angle), vy + ax * Math.sin(angle) + ay * Math.cos(angle));
        }
      } else {
        wedge.push(vx + ax, vy + ay);
        // The miter is 1 / cos(turn / 2) stroke widths long, and ends at the bend plus (a + b) / (1 + cos turn).
        if (join === "miter" && 1 / Math.cos(Math.abs(turn) / 2) <= miterLimit) {
          const reach = 1 / (1 + Math.cos(turn));
          wedge.push(vx + (ax + bx) * reach, vy + (ay + by) * reach);
        }
        wedge.push(vx + bx, vy + by);
      }
    }
    addPolygon(edges, wedge, true);
  }
}

// What one fill or stroke paints: its edges sorted by top, and the state of a sweep down the picture.
function makePaint(edges, evenOdd, color, id) {
  const count = edges.top.length;
  if (count === 0) return null;
  const order = Uint32Array.from({ length: count }, (_, i) => i).sort((a, b) => edges.top[a] - edges.top[b]);
  const pick = (list, Type) => Type.from(order, (i) => list[i]);
  const bottom = pick(edges.bottom, Float64Array);
  return {
    top: pick(edges.top, Float64Array),
    bottom,
    x: pick(edges.x, Float64Array),
    slope: pick(edges.slope, Float64Array),
    direction: pick(edges.direction, Int8Array),
    count,
    next: 0, // The first edge not yet reached by the sweep,
    active: new Uint32Array(count), // the edges the sweep line crosses, ...
    crossings: new Float64Array(count), // ... and where, in the same order.
    live: 0,
    yFrom: edges.top[order[0]],
    yTo: bottom.reduce((most, value) => Math.max(most, value), -Infinity),
    evenOdd,
    color,
    id,
  };
}

// The runs [from, to) of x, as pairs in `spans`, that the paint covers on the line y.
function coveredSpans(paint, y, spans) {
  const { top, bottom, x, slope, direction, active, crossings } = paint;
  while (paint.next < paint.count && top[paint.next] <= y) {
    if (bottom[paint.next] > y) active[paint.live++] = paint.next;
    paint.next++;
  }
  let live = 0;
  for (let k = 0; k < paint.live; k++) {
    const edge = active[k];
    if (bottom[edge] > y) active[live++] = edge;
  }
  paint.live = live;
  for (let k = 0; k < live; k++) { // Insertion sort by x; the order changes little from line to line.
    const edge = active[k];
    const at = x[edge] + (y - top[edge]) * slope[edge];
    let j = k;
    for (; j > 0 && crossings[j - 1] > at; j--) {
      crossings[j] = crossings[j - 1];
      active[j] = active[j - 1];
    }
    crossings[j] = at;
    active[j] = edge;
  }
  spans.length = 0;
  let winding = 0;
  let from = 0;
  for (let k = 0; k < live; k++) {
    const before = paint.evenOdd ? (winding & 1) !== 0 : winding !== 0;
    winding += direction[active[k]];
    const after = paint.evenOdd ? (winding & 1) !== 0 : winding !== 0;
    if (!before && after) from = crossings[k];
    else if (before && !after && crossings[k] > from) spans.push(from, crossings[k]);
  }
}

// Straight-alpha source-over of the colour r, g, b at `alpha` (0 to 1) onto the RGBA bytes at i.
function over(bytes, i, r, g, b, alpha) {
  const below = bytes[i + 3];
  if (below === 0) {
    const a = Math.round(alpha * 255);
    if (a === 0) return;
    bytes[i] = r;
    bytes[i + 1] = g;
    bytes[i + 2] = b;
    bytes[i + 3] = a;
    return;
  }
  const kept = (below / 255) * (1 - alpha);
  const total = alpha + kept;
  bytes[i] = Math.round((r * alpha + bytes[i] * kept) / total);
  bytes[i + 1] = Math.round((g * alpha + bytes[i + 1] * kept) / total);
  bytes[i + 2] = Math.round((b * alpha + bytes[i + 2] * kept) / total);
  bytes[i + 3] = Math.round(total * 255);
}

// A layer of samples drawn over another, its alpha scaled by `opacity`. The pixel style's layers
// also carry the id of the paint on top of each sample.
function composite(layer, target, opacity) {
  const { bytes } = layer;
  for (let s = 0; s < layer.words.length; s++) {
    const i = s * 4;
    if (bytes[i + 3] === 0) continue;
    over(target.bytes, i, bytes[i], bytes[i + 1], bytes[i + 2], (bytes[i + 3] / 255) * opacity);
    if (target.ids) target.ids[s] = layer.ids[s];
  }
}

function drawScene({ viewBox: [minX, minY, width, height], items }, size, style) {
  const smooth = style === "smooth";
  const S = smooth ? (size <= 256 ? 8 : 4) : size <= 128 ? 16 : 8; // Samples per pixel, in each direction.
  const scale = Math.min(size / width, size / height);
  const view = [scale, 0, 0, scale, (size - width * scale) / 2 - minX * scale, (size - height * scale) / 2 - minY * scale];

  // Every fill and stroke becomes a paint, numbered in painting order. A group with an opacity is
  // drawn as one, on a layer of its own that is then composited with that opacity.
  let paintCount = 0;
  const addPaint = (edges, evenOdd, rgb, alpha) => {
    const a = Math.round(alpha * 255);
    const paint = a === 0 ? null : makePaint(edges, evenOdd, [...rgb, a], paintCount + 1);
    if (paint === null) return [];
    paintCount++;
    const word = new Uint8Array(4);
    word.set(paint.color);
    paint.word = new Uint32Array(word.buffer)[0];
    return [paint];
  };
  const collect = (list) => {
    const out = [];
    for (const item of list) {
      if (item.items) {
        const inner = collect(item.items);
        if (inner.length > 0) {
          out.push({ opacity: item.opacity, items: inner, yFrom: Math.min(...inner.map((i) => i.yFrom)), yTo: Math.max(...inner.map((i) => i.yTo)) });
        }
        continue;
      }
      const m = multiply(view, item.matrix);
      const area = Math.abs(m[0] * m[3] - m[1] * m[2]);
      if (!(area > 0)) continue;
      const outlines = item.subpaths.map((subpath) => flatten(subpath, m));
      if (item.fill) {
        const edges = newEdges();
        for (const { points } of outlines) addPolygon(edges, points);
        out.push(...addPaint(edges, item.evenOdd, item.fill, item.fillAlpha));
      }
      if (item.stroke && item.strokeWidth > 0) {
        const edges = newEdges();
        for (const outline of outlines) addStroke(edges, outline, (item.strokeWidth * Math.sqrt(area)) / 2, item.join, item.miterLimit);
        out.push(...addPaint(edges, false, item.stroke, 1));
      }
    }
    return out;
  };
  const picture = collect(items);

  // One row of pixels at a time: S lines of samples, each paint's spans painted over the one before.
  // A sample is RGBA bytes in straight alpha; the pixel style keeps beside it the id of the paint on top.
  const rowSamples = size * S;
  const newLayer = () => {
    const words = new Uint32Array(rowSamples * S);
    return { words, bytes: new Uint8Array(words.buffer), ids: smooth ? null : new Uint32Array(rowSamples * S) };
  };
  const clear = (layer) => {
    layer.words.fill(0);
    layer.ids?.fill(0);
  };
  const layers = [newLayer()]; // The picture's own, then one for each depth of group.
  const spans = [];
  const draw = (list, depth, row) => {
    const { words, bytes, ids } = layers[depth];
    for (const item of list) {
      if (item.yTo <= row || item.yFrom >= row + 1) continue;
      if (item.items) {
        const layer = (layers[depth + 1] ??= newLayer());
        clear(layer);
        draw(item.items, depth + 1, row);
        composite(layer, layers[depth], item.opacity);
        continue;
      }
      const [r, g, b, a] = item.color;
      for (let line = 0; line < S; line++) {
        coveredSpans(item, row + (line + 0.5) / S, spans);
        for (let k = 0; k < spans.length; k += 2) {
          // A sample is covered when its centre is.
          const from = line * rowSamples + Math.max(0, Math.ceil(spans[k] * S - 0.5));
          const to = line * rowSamples + Math.min(rowSamples, Math.ceil(spans[k + 1] * S - 0.5));
          if (to <= from || to > (line + 1) * rowSamples) continue;
          if (a === 255) words.fill(item.word, from, to);
          else for (let i = from; i < to; i++) over(bytes, i * 4, r, g, b, a / 255);
          ids?.fill(item.id, from, to);
        }
      }
    }
  };

  const { words, bytes, ids } = layers[0];
  const data = new Uint8Array(size * size * 4);
  const colors = []; // The distinct colours of one pixel's samples (pixel style): the colour word, ...
  const shares = []; // ... how many samples have it, ...
  const latest = []; // ... the last paint among them, ...
  const first = []; // ... and where one of them is.
  for (let row = 0; row < size; row++) {
    clear(layers[0]);
    draw(picture, 0, row);
    for (let x = 0; x < size; x++) {
      const out = (row * size + x) * 4;
      if (smooth) {
        // The samples' colours averaged, each weighted by its alpha.
        let alpha = 0;
        let r = 0;
        let g = 0;
        let b = 0;
        for (let line = 0; line < S; line++) {
          for (let i = (line * rowSamples + x * S) * 4, end = i + S * 4; i < end; i += 4) {
            const a = bytes[i + 3];
            alpha += a;
            r += bytes[i] * a;
            g += bytes[i + 1] * a;
            b += bytes[i + 2] * a;
          }
        }
        const coverage = Math.round(alpha / (S * S));
        if (coverage === 0) continue;
        data.set([Math.round(r / alpha), Math.round(g / alpha), Math.round(b / alpha), coverage], out);
      } else {
        // The colour on most of the pixel's samples wins; of equal shares, the one painted last.
        let kinds = 0;
        for (let line = 0; line < S; line++) {
          for (let s = line * rowSamples + x * S, end = s + S; s < end; s++) {
            const empty = bytes[s * 4 + 3] === 0;
            const color = empty ? 0 : words[s];
            let k = 0;
            while (k < kinds && colors[k] !== color) k++;
            if (k === kinds) {
              colors[k] = color;
              shares[k] = 0;
              latest[k] = 0;
              first[k] = s * 4;
              kinds++;
            }
            shares[k]++;
            if (!empty && ids[s] > latest[k]) latest[k] = ids[s];
          }
        }
        let best = 0;
        for (let k = 1; k < kinds; k++) {
          if (shares[k] > shares[best] || (shares[k] === shares[best] && latest[k] > latest[best])) best = k;
        }
        if (colors[best] !== 0) data.set(bytes.subarray(first[best], first[best] + 4), out);
      }
    }
  }
  return { width: size, height: size, data };
}

export function rasterize(svg, size, { style } = {}) {
  if (!STYLES.includes(style)) throw new Error(`rasterize needs a style of ${STYLES.join(" or ")}, not ${style}`);
  if (!Number.isInteger(size) || size < 1 || size > MAX_SIZE) throw new Error(`rasterize needs a size of 1 to ${MAX_SIZE} pixels, not ${size}`);
  if (typeof svg !== "string") throw new Error("rasterize needs the SVG as a string");
  return drawScene(readSvg(svg), size, style);
}

// Each source pixel becomes a factor x factor block.
function enlarge({ width, height, data }, factor) {
  if (!Number.isInteger(factor) || factor < 1) throw new Error(`Pixel pictures only enlarge by whole numbers, not ${factor}`);
  const source = new Uint32Array(data.buffer, data.byteOffset, width * height);
  const large = new Uint32Array(width * factor * height * factor);
  for (let y = 0; y < height; y++) {
    const row = y * factor * width * factor;
    for (let x = 0; x < width; x++) large.fill(source[y * width + x], row + x * factor, row + (x + 1) * factor);
    for (let k = 1; k < factor; k++) large.copyWithin(row + k * width * factor, row, row + width * factor);
  }
  return { width: width * factor, height: height * factor, data: new Uint8Array(large.buffer) };
}

// ---- A Windows 95 document ---------------------------------------------------------

// A white page with a folded grey corner and the picture at half size on it. The page's outlines
// are half as thick as a 16-unit picture's own, so they match the picture's on the page.
export function documentSvg(svg) {
  let root = null;
  let depth = 0;
  let inner = "";
  for (const tag of markup(svg)) {
    if (root === null) {
      if (tag.closing || tag.name !== "svg") throw new Error(`The SVG needs a root <svg> element, not <${tag.name}>`);
      root = tag;
      if (tag.selfClosing) break;
      depth = 1;
    } else {
      depth += tag.closing ? -1 : tag.selfClosing ? 0 : 1;
      if (depth === 0) {
        inner = svg.slice(root.end, tag.start);
        break;
      }
    }
  }
  if (root === null) throw new Error("The SVG needs a root <svg> element");
  if (!root.selfClosing && depth !== 0) throw new Error("The SVG is not well-formed XML: <svg> is never closed");
  const [minX, minY, width, height] = parseViewBox(root.attributes);
  if (root.attributes.transform !== undefined) throw new Error("Unsupported attribute transform on <svg>");

  const scale = 8 / Math.max(width, height);
  const x = 4 + (8 - width * scale) / 2 - minX * scale;
  const y = 5.5 + (8 - height * scale) / 2 - minY * scale;
  const number = (value) => String(+value.toFixed(6));
  // The picture's own <svg> becomes a group that starts from SVG's defaults and keeps what the
  // picture sets there; what only sizes it (width, height, viewBox, xmlns, ...) is dropped.
  const group = { fill: "#000", stroke: "none", "stroke-width": "1", "stroke-linejoin": "miter", "stroke-miterlimit": "4" };
  for (const [name, value] of Object.entries(root.attributes)) {
    if (!/^(?:id|version|width|height|viewBox|xmlns(?::.+)?|data-.+)$/.test(name)) group[name] = value;
  }
  group.transform = `translate(${number(x)} ${number(y)}) scale(${number(scale)})`;
  const escape = (value) => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const attributes = Object.entries(group).map(([name, value]) => `${name}="${escape(value)}"`).join(" ");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" stroke-linejoin="round">
<path d="M3.25 .25H9.75L12.75 3.25V15.75H3.25Z" fill="#fff" stroke="#000" stroke-width=".5"/>
<path d="M9.75 .25V3.25H12.75" fill="#c0c0c0" stroke="#000" stroke-width=".5"/>
<g ${attributes}>${inner}</g>
</svg>`;
}

// ---- File formats ---------------------------------------------------------------------

const CRC_TABLE = Uint32Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(...buffers) {
  let c = 0xffffffff;
  for (const buffer of buffers) for (const byte of buffer) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function checkImage({ width, height, data }) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || !(data instanceof Uint8Array) || data.length !== width * height * 4) {
    throw new Error("An image needs a width, a height and width x height x 4 bytes of RGBA data");
  }
}

export function encodePng(image) {
  checkImage(image);
  const { width, height, data } = image;
  const chunk = (type, body) => {
    const head = Buffer.alloc(8);
    head.writeUInt32BE(body.length);
    head.write(type, 4, "latin1");
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(head.subarray(4), body));
    return Buffer.concat([head, body, crc]);
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header.set([8, 6, 0, 0, 0], 8); // 8-bit RGBA, no interlace.
  const rows = Buffer.alloc(height * (width * 4 + 1)); // Each row starts with filter type 0.
  for (let y = 0; y < height; y++) rows.set(data.subarray(y * width * 4, (y + 1) * width * 4), y * (width * 4 + 1) + 1);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", header),
    chunk("IDAT", zlib.deflateSync(rows, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

// PNG images in an ICO container.
export function encodeIco(imageAt) {
  const images = ICO_SIZES.map((size) => ({ size, data: encodePng(imageAt(size)) }));
  const header = Buffer.alloc(6 + images.length * 16);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = header.length;
  images.forEach(({ size, data }, i) => {
    const entry = 6 + i * 16;
    header[entry] = size === 256 ? 0 : size;
    header[entry + 1] = size === 256 ? 0 : size;
    header.writeUInt16LE(1, entry + 4);
    header.writeUInt16LE(32, entry + 6);
    header.writeUInt32LE(data.length, entry + 8);
    header.writeUInt32LE(offset, entry + 12);
    offset += data.length;
  });
  return Buffer.concat([header, ...images.map((image) => image.data)]);
}

// The small icns sizes: "ARGB", then each channel run-length compressed.
function encodeArgb({ width, height, data }) {
  const parts = [Buffer.from("ARGB", "latin1")];
  for (const channel of [3, 0, 1, 2]) {
    const bytes = Uint8Array.from({ length: width * height }, (_, i) => data[i * 4 + channel]);
    const out = [];
    for (let i = 0; i < bytes.length; ) {
      let run = 1;
      while (i + run < bytes.length && run < 130 && bytes[i + run] === bytes[i]) run++;
      if (run >= 3) {
        out.push(run + 125, bytes[i]);
        i += run;
        continue;
      }
      let end = i + 1;
      while (end < bytes.length && end - i < 128 && !(bytes[end] === bytes[end + 1] && bytes[end] === bytes[end + 2])) end++;
      out.push(end - i - 1, ...bytes.subarray(i, end));
      i = end;
    }
    parts.push(Buffer.from(out));
  }
  return Buffer.concat(parts);
}

export function encodeIcns(imageAt) {
  const chunks = ICNS_ENTRIES.map(([type, size, format]) => {
    const body = format === "png" ? encodePng(imageAt(size)) : encodeArgb(imageAt(size));
    const head = Buffer.alloc(8);
    head.write(type, 0, "latin1");
    head.writeUInt32BE(body.length + 8, 4);
    return Buffer.concat([head, body]);
  });
  const head = Buffer.alloc(8);
  head.write("icns", 0, "latin1");
  head.writeUInt32BE(8 + chunks.reduce((sum, chunk) => sum + chunk.length, 0), 4);
  return Buffer.concat([head, ...chunks]);
}

// ---- Making the files -------------------------------------------------------------------

// The picture of an icon at any size, each drawn once: the pixel style enlarges its master drawing.
function imageSource(scene, { style, master = 32 }) {
  const made = new Map();
  const make = (size) => {
    if (style === "smooth" || size <= Math.max(master, Math.max(...DRAWN_SIZES))) return drawScene(scene, size, style);
    return enlarge(imageAt(master), size / master);
  };
  const imageAt = (size) => {
    if (!made.has(size)) made.set(size, make(size));
    return made.get(size);
  };
  return imageAt;
}

export async function generateIcons(repoRoot, { log = console.log } = {}) {
  const icons = await readIconList(repoRoot);
  if (icons.length === 0) {
    log(`${MANIFEST} lists no icons.`);
    return [];
  }
  // Read and check every icon before writing any.
  const sources = [];
  for (const [index, icon] of icons.entries()) {
    let svg;
    try {
      svg = await readFile(path.join(repoRoot, icon.svg), "utf8");
    } catch (err) {
      throw new Error(`${MANIFEST}: icons[${index}].svg "${icon.svg}" cannot be read (${err.message})`, { cause: err });
    }
    try {
      sources.push(imageSource(readSvg(icon.document ? documentSvg(svg) : svg), icon));
    } catch (err) {
      throw new Error(`${MANIFEST}: icons[${index}] (${icon.svg}): ${err.message}`, { cause: err });
    }
  }

  const outputDir = path.join(repoRoot, ICON_DIR);
  await mkdir(outputDir, { recursive: true });
  const written = [];
  for (const [index, icon] of icons.entries()) {
    const imageAt = sources[index];
    const files = [
      [`${icon.name}.png`, () => encodePng(imageAt(PNG_SIZE))],
      [`${icon.name}.ico`, () => encodeIco(imageAt)],
      [`${icon.name}.icns`, () => encodeIcns(imageAt)],
    ];
    for (const [file, encode] of files) {
      const target = path.join(outputDir, file);
      await writeFile(target, encode());
      written.push(target);
    }
    log(`${icon.name}: wrote ${ICON_DIR}/${icon.name}.png, .ico and .icns`);
  }
  return written;
}

// ---- Command line -------------------------------------------------------------------------

function isEntryScript() {
  try {
    return realpathSync.native(process.argv[1]) === realpathSync.native(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

// Exit code 0 when the icons are made, 1 with the reason on stderr when not.
if (isEntryScript()) {
  try {
    await generateIcons(process.cwd());
  } catch (err) {
    console.error(err.message);
    process.exitCode = 1;
  }
}
