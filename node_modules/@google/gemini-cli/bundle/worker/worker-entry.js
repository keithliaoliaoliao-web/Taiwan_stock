const require = (await import('node:module')).createRequire(import.meta.url); const __chunk_filename = (await import('node:url')).fileURLToPath(import.meta.url); const __chunk_dirname = (await import('node:path')).dirname(__chunk_filename);
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// node_modules/mnemonist/utils/comparators.js
var require_comparators = __commonJS({
  "node_modules/mnemonist/utils/comparators.js"(exports) {
    var DEFAULT_COMPARATOR = function(a, b) {
      if (a < b)
        return -1;
      if (a > b)
        return 1;
      return 0;
    };
    var DEFAULT_REVERSE_COMPARATOR = function(a, b) {
      if (a < b)
        return 1;
      if (a > b)
        return -1;
      return 0;
    };
    function reverseComparator(comparator) {
      return function(a, b) {
        return comparator(b, a);
      };
    }
    function createTupleComparator(size) {
      if (size === 2) {
        return function(a, b) {
          if (a[0] < b[0])
            return -1;
          if (a[0] > b[0])
            return 1;
          if (a[1] < b[1])
            return -1;
          if (a[1] > b[1])
            return 1;
          return 0;
        };
      }
      return function(a, b) {
        var i = 0;
        while (i < size) {
          if (a[i] < b[i])
            return -1;
          if (a[i] > b[i])
            return 1;
          i++;
        }
        return 0;
      };
    }
    exports.DEFAULT_COMPARATOR = DEFAULT_COMPARATOR;
    exports.DEFAULT_REVERSE_COMPARATOR = DEFAULT_REVERSE_COMPARATOR;
    exports.reverseComparator = reverseComparator;
    exports.createTupleComparator = createTupleComparator;
  }
});

// node_modules/obliterator/support.js
var require_support = __commonJS({
  "node_modules/obliterator/support.js"(exports) {
    exports.ARRAY_BUFFER_SUPPORT = typeof ArrayBuffer !== "undefined";
    exports.SYMBOL_SUPPORT = typeof Symbol !== "undefined";
  }
});

// node_modules/obliterator/foreach.js
var require_foreach = __commonJS({
  "node_modules/obliterator/foreach.js"(exports, module) {
    var support = require_support();
    var ARRAY_BUFFER_SUPPORT = support.ARRAY_BUFFER_SUPPORT;
    var SYMBOL_SUPPORT = support.SYMBOL_SUPPORT;
    module.exports = function forEach(iterable, callback) {
      var iterator, k, i, l, s;
      if (!iterable) throw new Error("obliterator/forEach: invalid iterable.");
      if (typeof callback !== "function")
        throw new Error("obliterator/forEach: expecting a callback.");
      if (Array.isArray(iterable) || ARRAY_BUFFER_SUPPORT && ArrayBuffer.isView(iterable) || typeof iterable === "string" || iterable.toString() === "[object Arguments]") {
        for (i = 0, l = iterable.length; i < l; i++) callback(iterable[i], i);
        return;
      }
      if (typeof iterable.forEach === "function") {
        iterable.forEach(callback);
        return;
      }
      if (SYMBOL_SUPPORT && Symbol.iterator in iterable && typeof iterable.next !== "function") {
        iterable = iterable[Symbol.iterator]();
      }
      if (typeof iterable.next === "function") {
        iterator = iterable;
        i = 0;
        while (s = iterator.next(), s.done !== true) {
          callback(s.value, i);
          i++;
        }
        return;
      }
      for (k in iterable) {
        if (iterable.hasOwnProperty(k)) {
          callback(iterable[k], k);
        }
      }
      return;
    };
  }
});

// node_modules/mnemonist/fibonacci-heap.js
var require_fibonacci_heap = __commonJS({
  "node_modules/mnemonist/fibonacci-heap.js"(exports, module) {
    var comparators = require_comparators();
    var forEach = require_foreach();
    var DEFAULT_COMPARATOR = comparators.DEFAULT_COMPARATOR;
    var reverseComparator = comparators.reverseComparator;
    function FibonacciHeap2(comparator) {
      this.clear();
      this.comparator = comparator || DEFAULT_COMPARATOR;
      if (typeof this.comparator !== "function")
        throw new Error("mnemonist/FibonacciHeap.constructor: given comparator should be a function.");
    }
    FibonacciHeap2.prototype.clear = function() {
      this.root = null;
      this.min = null;
      this.size = 0;
    };
    function createNode(item) {
      return {
        item,
        degree: 0
      };
    }
    function mergeWithRoot(heap, node) {
      if (!heap.root) {
        heap.root = node;
      } else {
        node.right = heap.root.right;
        node.left = heap.root;
        heap.root.right.left = node;
        heap.root.right = node;
      }
    }
    FibonacciHeap2.prototype.push = function(item) {
      var node = createNode(item);
      node.left = node;
      node.right = node;
      mergeWithRoot(this, node);
      if (!this.min || this.comparator(node.item, this.min.item) <= 0)
        this.min = node;
      return ++this.size;
    };
    FibonacciHeap2.prototype.peek = function() {
      return this.min ? this.min.item : void 0;
    };
    function consumeLinkedList(head) {
      var nodes = [], node = head, flag = false;
      while (true) {
        if (node === head && flag)
          break;
        else if (node === head)
          flag = true;
        nodes.push(node);
        node = node.right;
      }
      return nodes;
    }
    function removeFromRoot(heap, node) {
      if (heap.root === node)
        heap.root = node.right;
      node.left.right = node.right;
      node.right.left = node.left;
    }
    function mergeWithChild(parent, node) {
      if (!parent.child) {
        parent.child = node;
      } else {
        node.right = parent.child.right;
        node.left = parent.child;
        parent.child.right.left = node;
        parent.child.right = node;
      }
    }
    function link2(heap, y, x) {
      removeFromRoot(heap, y);
      y.left = y;
      y.right = y;
      mergeWithChild(x, y);
      x.degree++;
      y.parent = x;
    }
    function consolidate(heap) {
      var A = new Array(heap.size), nodes = consumeLinkedList(heap.root), i, l, x, y, d, t;
      for (i = 0, l = nodes.length; i < l; i++) {
        x = nodes[i];
        d = x.degree;
        while (A[d]) {
          y = A[d];
          if (heap.comparator(x.item, y.item) > 0) {
            t = x;
            x = y;
            y = t;
          }
          link2(heap, y, x);
          A[d] = null;
          d++;
        }
        A[d] = x;
      }
      for (i = 0; i < heap.size; i++) {
        if (A[i] && heap.comparator(A[i].item, heap.min.item) <= 0)
          heap.min = A[i];
      }
    }
    FibonacciHeap2.prototype.pop = function() {
      if (!this.size)
        return void 0;
      var z = this.min;
      if (z.child) {
        var nodes = consumeLinkedList(z.child), node, i, l;
        for (i = 0, l = nodes.length; i < l; i++) {
          node = nodes[i];
          mergeWithRoot(this, node);
          delete node.parent;
        }
      }
      removeFromRoot(this, z);
      if (z === z.right) {
        this.min = null;
        this.root = null;
      } else {
        this.min = z.right;
        consolidate(this);
      }
      this.size--;
      return z.item;
    };
    FibonacciHeap2.prototype.inspect = function() {
      var proxy = {
        size: this.size
      };
      if (this.min && "item" in this.min)
        proxy.top = this.min.item;
      Object.defineProperty(proxy, "constructor", {
        value: FibonacciHeap2,
        enumerable: false
      });
      return proxy;
    };
    if (typeof Symbol !== "undefined")
      FibonacciHeap2.prototype[Symbol.for("nodejs.util.inspect.custom")] = FibonacciHeap2.prototype.inspect;
    function MaxFibonacciHeap2(comparator) {
      this.clear();
      this.comparator = comparator || DEFAULT_COMPARATOR;
      if (typeof this.comparator !== "function")
        throw new Error("mnemonist/FibonacciHeap.constructor: given comparator should be a function.");
      this.comparator = reverseComparator(this.comparator);
    }
    MaxFibonacciHeap2.prototype = FibonacciHeap2.prototype;
    FibonacciHeap2.from = function(iterable, comparator) {
      var heap = new FibonacciHeap2(comparator);
      forEach(iterable, function(value) {
        heap.push(value);
      });
      return heap;
    };
    MaxFibonacciHeap2.from = function(iterable, comparator) {
      var heap = new MaxFibonacciHeap2(comparator);
      forEach(iterable, function(value) {
        heap.push(value);
      });
      return heap;
    };
    FibonacciHeap2.MinFibonacciHeap = FibonacciHeap2;
    FibonacciHeap2.MaxFibonacciHeap = MaxFibonacciHeap2;
    module.exports = FibonacciHeap2;
  }
});

// node_modules/mnemonist/utils/typed-arrays.js
var require_typed_arrays = __commonJS({
  "node_modules/mnemonist/utils/typed-arrays.js"(exports) {
    var MAX_8BIT_INTEGER = Math.pow(2, 8) - 1;
    var MAX_16BIT_INTEGER = Math.pow(2, 16) - 1;
    var MAX_32BIT_INTEGER = Math.pow(2, 32) - 1;
    var MAX_SIGNED_8BIT_INTEGER = Math.pow(2, 7) - 1;
    var MAX_SIGNED_16BIT_INTEGER = Math.pow(2, 15) - 1;
    var MAX_SIGNED_32BIT_INTEGER = Math.pow(2, 31) - 1;
    exports.getPointerArray = function(size) {
      var maxIndex = size - 1;
      if (maxIndex <= MAX_8BIT_INTEGER)
        return Uint8Array;
      if (maxIndex <= MAX_16BIT_INTEGER)
        return Uint16Array;
      if (maxIndex <= MAX_32BIT_INTEGER)
        return Uint32Array;
      throw new Error("mnemonist: Pointer Array of size > 4294967295 is not supported.");
    };
    exports.getSignedPointerArray = function(size) {
      var maxIndex = size - 1;
      if (maxIndex <= MAX_SIGNED_8BIT_INTEGER)
        return Int8Array;
      if (maxIndex <= MAX_SIGNED_16BIT_INTEGER)
        return Int16Array;
      if (maxIndex <= MAX_SIGNED_32BIT_INTEGER)
        return Int32Array;
      return Float64Array;
    };
    exports.getNumberType = function(value) {
      if (value === (value | 0)) {
        if (Math.sign(value) === -1) {
          if (value <= 127 && value >= -128)
            return Int8Array;
          if (value <= 32767 && value >= -32768)
            return Int16Array;
          return Int32Array;
        } else {
          if (value <= 255)
            return Uint8Array;
          if (value <= 65535)
            return Uint16Array;
          return Uint32Array;
        }
      }
      return Float64Array;
    };
    var TYPE_PRIORITY = {
      Uint8Array: 1,
      Int8Array: 2,
      Uint16Array: 3,
      Int16Array: 4,
      Uint32Array: 5,
      Int32Array: 6,
      Float32Array: 7,
      Float64Array: 8
    };
    exports.getMinimalRepresentation = function(array, getter) {
      var maxType = null, maxPriority = 0, p, t, v, i, l;
      for (i = 0, l = array.length; i < l; i++) {
        v = getter ? getter(array[i]) : array[i];
        t = exports.getNumberType(v);
        p = TYPE_PRIORITY[t.name];
        if (p > maxPriority) {
          maxPriority = p;
          maxType = t;
        }
      }
      return maxType;
    };
    exports.isTypedArray = function(value) {
      return typeof ArrayBuffer !== "undefined" && ArrayBuffer.isView(value);
    };
    exports.concat = function() {
      var length = 0, i, o, l;
      for (i = 0, l = arguments.length; i < l; i++)
        length += arguments[i].length;
      var array = new arguments[0].constructor(length);
      for (i = 0, o = 0; i < l; i++) {
        array.set(arguments[i], o);
        o += arguments[i].length;
      }
      return array;
    };
    exports.indices = function(length) {
      var PointerArray = exports.getPointerArray(length);
      var array = new PointerArray(length);
      for (var i = 0; i < length; i++)
        array[i] = i;
      return array;
    };
  }
});

// node_modules/mnemonist/utils/iterables.js
var require_iterables = __commonJS({
  "node_modules/mnemonist/utils/iterables.js"(exports) {
    var forEach = require_foreach();
    var typed = require_typed_arrays();
    function isArrayLike(target) {
      return Array.isArray(target) || typed.isTypedArray(target);
    }
    function guessLength(target) {
      if (typeof target.length === "number")
        return target.length;
      if (typeof target.size === "number")
        return target.size;
      return;
    }
    function toArray(target) {
      var l = guessLength(target);
      var array = typeof l === "number" ? new Array(l) : [];
      var i = 0;
      forEach(target, function(value) {
        array[i++] = value;
      });
      return array;
    }
    function toArrayWithIndices(target) {
      var l = guessLength(target);
      var IndexArray = typeof l === "number" ? typed.getPointerArray(l) : Array;
      var array = typeof l === "number" ? new Array(l) : [];
      var indices = typeof l === "number" ? new IndexArray(l) : [];
      var i = 0;
      forEach(target, function(value) {
        array[i] = value;
        indices[i] = i++;
      });
      return [array, indices];
    }
    exports.isArrayLike = isArrayLike;
    exports.guessLength = guessLength;
    exports.toArray = toArray;
    exports.toArrayWithIndices = toArrayWithIndices;
  }
});

// node_modules/mnemonist/heap.js
var require_heap = __commonJS({
  "node_modules/mnemonist/heap.js"(exports, module) {
    var forEach = require_foreach();
    var comparators = require_comparators();
    var iterables = require_iterables();
    var DEFAULT_COMPARATOR = comparators.DEFAULT_COMPARATOR;
    var reverseComparator = comparators.reverseComparator;
    function siftDown(compare, heap, startIndex, i) {
      var item = heap[i], parentIndex, parent;
      while (i > startIndex) {
        parentIndex = i - 1 >> 1;
        parent = heap[parentIndex];
        if (compare(item, parent) < 0) {
          heap[i] = parent;
          i = parentIndex;
          continue;
        }
        break;
      }
      heap[i] = item;
    }
    function siftUp(compare, heap, i) {
      var endIndex = heap.length, startIndex = i, item = heap[i], childIndex = 2 * i + 1, rightIndex;
      while (childIndex < endIndex) {
        rightIndex = childIndex + 1;
        if (rightIndex < endIndex && compare(heap[childIndex], heap[rightIndex]) >= 0) {
          childIndex = rightIndex;
        }
        heap[i] = heap[childIndex];
        i = childIndex;
        childIndex = 2 * i + 1;
      }
      heap[i] = item;
      siftDown(compare, heap, startIndex, i);
    }
    function push(compare, heap, item) {
      heap.push(item);
      siftDown(compare, heap, 0, heap.length - 1);
    }
    function pop(compare, heap) {
      var lastItem = heap.pop();
      if (heap.length !== 0) {
        var item = heap[0];
        heap[0] = lastItem;
        siftUp(compare, heap, 0);
        return item;
      }
      return lastItem;
    }
    function replace(compare, heap, item) {
      if (heap.length === 0)
        throw new Error("mnemonist/heap.replace: cannot pop an empty heap.");
      var popped = heap[0];
      heap[0] = item;
      siftUp(compare, heap, 0);
      return popped;
    }
    function pushpop(compare, heap, item) {
      var tmp;
      if (heap.length !== 0 && compare(heap[0], item) < 0) {
        tmp = heap[0];
        heap[0] = item;
        item = tmp;
        siftUp(compare, heap, 0);
      }
      return item;
    }
    function heapify(compare, array) {
      var n = array.length, l = n >> 1, i = l;
      while (--i >= 0)
        siftUp(compare, array, i);
    }
    function consume(compare, heap) {
      var l = heap.length, i = 0;
      var array = new Array(l);
      while (i < l)
        array[i++] = pop(compare, heap);
      return array;
    }
    function nsmallest(compare, n, iterable) {
      if (arguments.length === 2) {
        iterable = n;
        n = compare;
        compare = DEFAULT_COMPARATOR;
      }
      var reverseCompare = reverseComparator(compare);
      var i, l, v;
      var min = Infinity;
      var result;
      if (n === 1) {
        if (iterables.isArrayLike(iterable)) {
          for (i = 0, l = iterable.length; i < l; i++) {
            v = iterable[i];
            if (min === Infinity || compare(v, min) < 0)
              min = v;
          }
          result = new iterable.constructor(1);
          result[0] = min;
          return result;
        }
        forEach(iterable, function(value) {
          if (min === Infinity || compare(value, min) < 0)
            min = value;
        });
        return [min];
      }
      if (iterables.isArrayLike(iterable)) {
        if (n >= iterable.length)
          return iterable.slice().sort(compare);
        result = iterable.slice(0, n);
        heapify(reverseCompare, result);
        for (i = n, l = iterable.length; i < l; i++)
          if (reverseCompare(iterable[i], result[0]) > 0)
            replace(reverseCompare, result, iterable[i]);
        return result.sort(compare);
      }
      var size = iterables.guessLength(iterable);
      if (size !== null && size < n)
        n = size;
      result = new Array(n);
      i = 0;
      forEach(iterable, function(value) {
        if (i < n) {
          result[i] = value;
        } else {
          if (i === n)
            heapify(reverseCompare, result);
          if (reverseCompare(value, result[0]) > 0)
            replace(reverseCompare, result, value);
        }
        i++;
      });
      if (result.length > i)
        result.length = i;
      return result.sort(compare);
    }
    function nlargest(compare, n, iterable) {
      if (arguments.length === 2) {
        iterable = n;
        n = compare;
        compare = DEFAULT_COMPARATOR;
      }
      var reverseCompare = reverseComparator(compare);
      var i, l, v;
      var max = -Infinity;
      var result;
      if (n === 1) {
        if (iterables.isArrayLike(iterable)) {
          for (i = 0, l = iterable.length; i < l; i++) {
            v = iterable[i];
            if (max === -Infinity || compare(v, max) > 0)
              max = v;
          }
          result = new iterable.constructor(1);
          result[0] = max;
          return result;
        }
        forEach(iterable, function(value) {
          if (max === -Infinity || compare(value, max) > 0)
            max = value;
        });
        return [max];
      }
      if (iterables.isArrayLike(iterable)) {
        if (n >= iterable.length)
          return iterable.slice().sort(reverseCompare);
        result = iterable.slice(0, n);
        heapify(compare, result);
        for (i = n, l = iterable.length; i < l; i++)
          if (compare(iterable[i], result[0]) > 0)
            replace(compare, result, iterable[i]);
        return result.sort(reverseCompare);
      }
      var size = iterables.guessLength(iterable);
      if (size !== null && size < n)
        n = size;
      result = new Array(n);
      i = 0;
      forEach(iterable, function(value) {
        if (i < n) {
          result[i] = value;
        } else {
          if (i === n)
            heapify(compare, result);
          if (compare(value, result[0]) > 0)
            replace(compare, result, value);
        }
        i++;
      });
      if (result.length > i)
        result.length = i;
      return result.sort(reverseCompare);
    }
    function Heap2(comparator) {
      this.clear();
      this.comparator = comparator || DEFAULT_COMPARATOR;
      if (typeof this.comparator !== "function")
        throw new Error("mnemonist/Heap.constructor: given comparator should be a function.");
    }
    Heap2.prototype.clear = function() {
      this.items = [];
      this.size = 0;
    };
    Heap2.prototype.push = function(item) {
      push(this.comparator, this.items, item);
      return ++this.size;
    };
    Heap2.prototype.peek = function() {
      return this.items[0];
    };
    Heap2.prototype.pop = function() {
      if (this.size !== 0)
        this.size--;
      return pop(this.comparator, this.items);
    };
    Heap2.prototype.replace = function(item) {
      return replace(this.comparator, this.items, item);
    };
    Heap2.prototype.pushpop = function(item) {
      return pushpop(this.comparator, this.items, item);
    };
    Heap2.prototype.consume = function() {
      this.size = 0;
      return consume(this.comparator, this.items);
    };
    Heap2.prototype.toArray = function() {
      return consume(this.comparator, this.items.slice());
    };
    Heap2.prototype.inspect = function() {
      var proxy = this.toArray();
      Object.defineProperty(proxy, "constructor", {
        value: Heap2,
        enumerable: false
      });
      return proxy;
    };
    if (typeof Symbol !== "undefined")
      Heap2.prototype[Symbol.for("nodejs.util.inspect.custom")] = Heap2.prototype.inspect;
    function MaxHeap2(comparator) {
      this.clear();
      this.comparator = comparator || DEFAULT_COMPARATOR;
      if (typeof this.comparator !== "function")
        throw new Error("mnemonist/MaxHeap.constructor: given comparator should be a function.");
      this.comparator = reverseComparator(this.comparator);
    }
    MaxHeap2.prototype = Heap2.prototype;
    Heap2.from = function(iterable, comparator) {
      var heap = new Heap2(comparator);
      var items;
      if (iterables.isArrayLike(iterable))
        items = iterable.slice();
      else
        items = iterables.toArray(iterable);
      heapify(heap.comparator, items);
      heap.items = items;
      heap.size = items.length;
      return heap;
    };
    MaxHeap2.from = function(iterable, comparator) {
      var heap = new MaxHeap2(comparator);
      var items;
      if (iterables.isArrayLike(iterable))
        items = iterable.slice();
      else
        items = iterables.toArray(iterable);
      heapify(heap.comparator, items);
      heap.items = items;
      heap.size = items.length;
      return heap;
    };
    Heap2.siftUp = siftUp;
    Heap2.siftDown = siftDown;
    Heap2.push = push;
    Heap2.pop = pop;
    Heap2.replace = replace;
    Heap2.pushpop = pushpop;
    Heap2.heapify = heapify;
    Heap2.consume = consume;
    Heap2.nsmallest = nsmallest;
    Heap2.nlargest = nlargest;
    Heap2.MinHeap = Heap2;
    Heap2.MaxHeap = MaxHeap2;
    module.exports = Heap2;
  }
});

// node_modules/mnemonist/suffix-array.js
var require_suffix_array = __commonJS({
  "node_modules/mnemonist/suffix-array.js"(exports, module) {
    var SEPARATOR = "";
    function sort(string, array, offset) {
      var l = array.length, buckets = [], i = l, j = -1, b, d = 0, bits;
      while (i--)
        j = Math.max(string[array[i] + offset], j);
      bits = j >> 24 && 32 || j >> 16 && 24 || j >> 8 && 16 || 8;
      for (; d < bits; d += 4) {
        for (i = 16; i--; )
          buckets[i] = [];
        for (i = l; i--; )
          buckets[string[array[i] + offset] >> d & 15].push(array[i]);
        for (b = 0; b < 16; b++) {
          for (j = buckets[b].length; j--; )
            array[++i] = buckets[b][j];
        }
      }
    }
    function compare(string, lookup, m, n) {
      return string[m] - string[n] || (m % 3 === 2 ? string[m + 1] - string[n + 1] || lookup[m + 2] - lookup[n + 2] : lookup[m + 1] - lookup[n + 1]);
    }
    function build(string, l) {
      var a = [], b = [], al = 2 * l / 3 | 0, bl = l - al, r = al + 1 >> 1, i = al, j = 0, k, lookup = [], result = [];
      if (l === 1)
        return [0];
      while (i--)
        a[i] = (i * 3 >> 1) + 1;
      for (i = 3; i--; )
        sort(string, a, i);
      j = b[(a[0] / 3 | 0) + (a[0] % 3 === 1 ? 0 : r)] = 1;
      for (i = 1; i < al; i++) {
        if (string[a[i]] !== string[a[i - 1]] || string[a[i] + 1] !== string[a[i - 1] + 1] || string[a[i] + 2] !== string[a[i - 1] + 2])
          j++;
        b[(a[i] / 3 | 0) + (a[i] % 3 === 1 ? 0 : r)] = j;
      }
      if (j < al) {
        b = build(b, al);
        for (i = al; i--; )
          a[i] = b[i] < r ? b[i] * 3 + 1 : (b[i] - r) * 3 + 2;
      }
      for (i = al; i--; )
        lookup[a[i]] = i;
      lookup[l] = -1;
      lookup[l + 1] = -2;
      b = l % 3 === 1 ? [l - 1] : [];
      for (i = 0; i < al; i++) {
        if (a[i] % 3 === 1)
          b.push(a[i] - 1);
      }
      sort(string, b, 0);
      for (i = 0, j = 0, k = 0; i < al && j < bl; )
        result[k++] = compare(string, lookup, a[i], b[j]) < 0 ? a[i++] : b[j++];
      while (i < al)
        result[k++] = a[i++];
      while (j < bl)
        result[k++] = b[j++];
      return result;
    }
    function convert(target) {
      var length = target.length, paddingOffset = length % 3, array = new Array(length + paddingOffset), l, i;
      if (typeof target !== "string") {
        var uniqueTokens = /* @__PURE__ */ Object.create(null);
        for (i = 0; i < length; i++) {
          if (!uniqueTokens[target[i]])
            uniqueTokens[target[i]] = true;
        }
        var alphabet = /* @__PURE__ */ Object.create(null), sortedUniqueTokens = Object.keys(uniqueTokens).sort();
        for (i = 0, l = sortedUniqueTokens.length; i < l; i++)
          alphabet[sortedUniqueTokens[i]] = i + 1;
        for (i = 0; i < length; i++) {
          array[i] = alphabet[target[i]];
        }
      } else {
        for (i = 0; i < length; i++)
          array[i] = target.charCodeAt(i);
      }
      for (i = length; i < length + paddingOffset; i++)
        array[i] = 0;
      return array;
    }
    function SuffixArray2(string) {
      this.hasArbitrarySequence = typeof string !== "string";
      this.string = string;
      this.length = string.length;
      this.array = build(convert(string), this.length);
    }
    SuffixArray2.prototype.toString = function() {
      return this.array.join(",");
    };
    SuffixArray2.prototype.toJSON = function() {
      return this.array;
    };
    SuffixArray2.prototype.inspect = function() {
      var array = new Array(this.length);
      for (var i = 0; i < this.length; i++)
        array[i] = this.string.slice(this.array[i]);
      Object.defineProperty(array, "constructor", {
        value: SuffixArray2,
        enumerable: false
      });
      return array;
    };
    if (typeof Symbol !== "undefined")
      SuffixArray2.prototype[Symbol.for("nodejs.util.inspect.custom")] = SuffixArray2.prototype.inspect;
    function GeneralizedSuffixArray2(strings) {
      this.hasArbitrarySequence = typeof strings[0] !== "string";
      this.size = strings.length;
      if (this.hasArbitrarySequence) {
        this.text = [];
        for (var i = 0, l = this.size; i < l; i++) {
          this.text.push.apply(this.text, strings[i]);
          if (i < l - 1)
            this.text.push(SEPARATOR);
        }
      } else {
        this.text = strings.join(SEPARATOR);
      }
      this.firstLength = strings[0].length;
      this.length = this.text.length;
      this.array = build(convert(this.text), this.length);
    }
    GeneralizedSuffixArray2.prototype.longestCommonSubsequence = function() {
      var lcs = this.hasArbitrarySequence ? [] : "", lcp, i, j, s, t;
      for (i = 1; i < this.length; i++) {
        s = this.array[i];
        t = this.array[i - 1];
        if (s < this.firstLength && t < this.firstLength)
          continue;
        if (s > this.firstLength && t > this.firstLength)
          continue;
        lcp = Math.min(this.length - s, this.length - t);
        for (j = 0; j < lcp; j++) {
          if (this.text[s + j] !== this.text[t + j]) {
            lcp = j;
            break;
          }
        }
        if (lcp > lcs.length)
          lcs = this.text.slice(s, s + lcp);
      }
      return lcs;
    };
    GeneralizedSuffixArray2.prototype.toString = function() {
      return this.array.join(",");
    };
    GeneralizedSuffixArray2.prototype.toJSON = function() {
      return this.array;
    };
    GeneralizedSuffixArray2.prototype.inspect = function() {
      var array = new Array(this.length);
      for (var i = 0; i < this.length; i++)
        array[i] = this.text.slice(this.array[i]);
      Object.defineProperty(array, "constructor", {
        value: GeneralizedSuffixArray2,
        enumerable: false
      });
      return array;
    };
    if (typeof Symbol !== "undefined")
      GeneralizedSuffixArray2.prototype[Symbol.for("nodejs.util.inspect.custom")] = GeneralizedSuffixArray2.prototype.inspect;
    SuffixArray2.GeneralizedSuffixArray = GeneralizedSuffixArray2;
    module.exports = SuffixArray2;
  }
});

// node_modules/obliterator/iterator.js
var require_iterator = __commonJS({
  "node_modules/obliterator/iterator.js"(exports, module) {
    function Iterator(next) {
      if (typeof next !== "function")
        throw new Error("obliterator/iterator: expecting a function!");
      this.next = next;
    }
    if (typeof Symbol !== "undefined")
      Iterator.prototype[Symbol.iterator] = function() {
        return this;
      };
    Iterator.of = function() {
      var args = arguments, l = args.length, i = 0;
      return new Iterator(function() {
        if (i >= l) return { done: true };
        return { done: false, value: args[i++] };
      });
    };
    Iterator.empty = function() {
      var iterator = new Iterator(function() {
        return { done: true };
      });
      return iterator;
    };
    Iterator.fromSequence = function(sequence) {
      var i = 0, l = sequence.length;
      return new Iterator(function() {
        if (i >= l) return { done: true };
        return { done: false, value: sequence[i++] };
      });
    };
    Iterator.is = function(value) {
      if (value instanceof Iterator) return true;
      return typeof value === "object" && value !== null && typeof value.next === "function";
    };
    module.exports = Iterator;
  }
});

// node_modules/mnemonist/vector.js
var require_vector = __commonJS({
  "node_modules/mnemonist/vector.js"(exports, module) {
    var Iterator = require_iterator();
    var forEach = require_foreach();
    var iterables = require_iterables();
    var typed = require_typed_arrays();
    var DEFAULT_GROWING_POLICY = function(currentCapacity) {
      return Math.max(1, Math.ceil(currentCapacity * 1.5));
    };
    var pointerArrayFactory = function(capacity) {
      var PointerArray = typed.getPointerArray(capacity);
      return new PointerArray(capacity);
    };
    function Vector2(ArrayClass, initialCapacityOrOptions) {
      if (arguments.length < 1)
        throw new Error("mnemonist/vector: expecting at least a byte array constructor.");
      var initialCapacity = initialCapacityOrOptions || 0, policy = DEFAULT_GROWING_POLICY, initialLength = 0, factory = false;
      if (typeof initialCapacityOrOptions === "object") {
        initialCapacity = initialCapacityOrOptions.initialCapacity || 0;
        initialLength = initialCapacityOrOptions.initialLength || 0;
        policy = initialCapacityOrOptions.policy || policy;
        factory = initialCapacityOrOptions.factory === true;
      }
      this.factory = factory ? ArrayClass : null;
      this.ArrayClass = ArrayClass;
      this.length = initialLength;
      this.capacity = Math.max(initialLength, initialCapacity);
      this.policy = policy;
      this.array = new ArrayClass(this.capacity);
    }
    Vector2.prototype.set = function(index, value) {
      if (this.length < index)
        throw new Error("Vector(" + this.ArrayClass.name + ").set: index out of bounds.");
      this.array[index] = value;
      return this;
    };
    Vector2.prototype.get = function(index) {
      if (this.length < index)
        return void 0;
      return this.array[index];
    };
    Vector2.prototype.applyPolicy = function(override) {
      var newCapacity = this.policy(override || this.capacity);
      if (typeof newCapacity !== "number" || newCapacity < 0)
        throw new Error("mnemonist/vector.applyPolicy: policy returned an invalid value (expecting a positive integer).");
      if (newCapacity <= this.capacity)
        throw new Error("mnemonist/vector.applyPolicy: policy returned a less or equal capacity to allocate.");
      return newCapacity;
    };
    Vector2.prototype.reallocate = function(capacity) {
      if (capacity === this.capacity)
        return this;
      var oldArray = this.array;
      if (capacity < this.length)
        this.length = capacity;
      if (capacity > this.capacity) {
        if (this.factory === null)
          this.array = new this.ArrayClass(capacity);
        else
          this.array = this.factory(capacity);
        if (typed.isTypedArray(this.array)) {
          this.array.set(oldArray, 0);
        } else {
          for (var i = 0, l = this.length; i < l; i++)
            this.array[i] = oldArray[i];
        }
      } else {
        this.array = oldArray.slice(0, capacity);
      }
      this.capacity = capacity;
      return this;
    };
    Vector2.prototype.grow = function(capacity) {
      var newCapacity;
      if (typeof capacity === "number") {
        if (this.capacity >= capacity)
          return this;
        newCapacity = this.capacity;
        while (newCapacity < capacity)
          newCapacity = this.applyPolicy(newCapacity);
        this.reallocate(newCapacity);
        return this;
      }
      newCapacity = this.applyPolicy();
      this.reallocate(newCapacity);
      return this;
    };
    Vector2.prototype.resize = function(length) {
      if (length === this.length)
        return this;
      if (length < this.length) {
        this.length = length;
        return this;
      }
      this.length = length;
      this.reallocate(length);
      return this;
    };
    Vector2.prototype.push = function(value) {
      if (this.capacity === this.length)
        this.grow();
      this.array[this.length++] = value;
      return this.length;
    };
    Vector2.prototype.pop = function() {
      if (this.length === 0)
        return;
      return this.array[--this.length];
    };
    Vector2.prototype.values = function() {
      var items = this.array, l = this.length, i = 0;
      return new Iterator(function() {
        if (i >= l)
          return {
            done: true
          };
        var value = items[i];
        i++;
        return {
          value,
          done: false
        };
      });
    };
    Vector2.prototype.entries = function() {
      var items = this.array, l = this.length, i = 0;
      return new Iterator(function() {
        if (i >= l)
          return {
            done: true
          };
        var value = items[i];
        return {
          value: [i++, value],
          done: false
        };
      });
    };
    if (typeof Symbol !== "undefined")
      Vector2.prototype[Symbol.iterator] = Vector2.prototype.values;
    Vector2.prototype.inspect = function() {
      var proxy = this.array.slice(0, this.length);
      proxy.type = this.array.constructor.name;
      proxy.items = this.length;
      proxy.capacity = this.capacity;
      Object.defineProperty(proxy, "constructor", {
        value: Vector2,
        enumerable: false
      });
      return proxy;
    };
    if (typeof Symbol !== "undefined")
      Vector2.prototype[Symbol.for("nodejs.util.inspect.custom")] = Vector2.prototype.inspect;
    Vector2.from = function(iterable, ArrayClass, capacity) {
      if (arguments.length < 3) {
        capacity = iterables.guessLength(iterable);
        if (typeof capacity !== "number")
          throw new Error("mnemonist/vector.from: could not guess iterable length. Please provide desired capacity as last argument.");
      }
      var vector = new Vector2(ArrayClass, capacity);
      forEach(iterable, function(value) {
        vector.push(value);
      });
      return vector;
    };
    function subClass(ArrayClass) {
      var SubClass = function(initialCapacityOrOptions) {
        Vector2.call(this, ArrayClass, initialCapacityOrOptions);
      };
      for (var k in Vector2.prototype) {
        if (Vector2.prototype.hasOwnProperty(k))
          SubClass.prototype[k] = Vector2.prototype[k];
      }
      SubClass.from = function(iterable, capacity) {
        return Vector2.from(iterable, ArrayClass, capacity);
      };
      if (typeof Symbol !== "undefined")
        SubClass.prototype[Symbol.iterator] = SubClass.prototype.values;
      return SubClass;
    }
    Vector2.Int8Vector = subClass(Int8Array);
    Vector2.Uint8Vector = subClass(Uint8Array);
    Vector2.Uint8ClampedVector = subClass(Uint8ClampedArray);
    Vector2.Int16Vector = subClass(Int16Array);
    Vector2.Uint16Vector = subClass(Uint16Array);
    Vector2.Int32Vector = subClass(Int32Array);
    Vector2.Uint32Vector = subClass(Uint32Array);
    Vector2.Float32Vector = subClass(Float32Array);
    Vector2.Float64Vector = subClass(Float64Array);
    Vector2.PointerVector = subClass(pointerArrayFactory);
    module.exports = Vector2;
  }
});

// node_modules/mnemonist/lru-cache.js
var require_lru_cache = __commonJS({
  "node_modules/mnemonist/lru-cache.js"(exports, module) {
    var Iterator = require_iterator();
    var forEach = require_foreach();
    var typed = require_typed_arrays();
    var iterables = require_iterables();
    function LRUCache(Keys, Values, capacity) {
      if (arguments.length < 2) {
        capacity = Keys;
        Keys = null;
        Values = null;
      }
      this.capacity = capacity;
      if (typeof this.capacity !== "number" || this.capacity <= 0)
        throw new Error("mnemonist/lru-cache: capacity should be positive number.");
      else if (!isFinite(this.capacity) || Math.floor(this.capacity) !== this.capacity)
        throw new Error("mnemonist/lru-cache: capacity should be a finite positive integer.");
      var PointerArray = typed.getPointerArray(capacity);
      this.forward = new PointerArray(capacity);
      this.backward = new PointerArray(capacity);
      this.K = typeof Keys === "function" ? new Keys(capacity) : new Array(capacity);
      this.V = typeof Values === "function" ? new Values(capacity) : new Array(capacity);
      this.size = 0;
      this.head = 0;
      this.tail = 0;
      this.items = {};
    }
    LRUCache.prototype.clear = function() {
      this.size = 0;
      this.head = 0;
      this.tail = 0;
      this.items = {};
    };
    LRUCache.prototype.splayOnTop = function(pointer) {
      var oldHead = this.head;
      if (this.head === pointer)
        return this;
      var previous = this.backward[pointer], next = this.forward[pointer];
      if (this.tail === pointer) {
        this.tail = previous;
      } else {
        this.backward[next] = previous;
      }
      this.forward[previous] = next;
      this.backward[oldHead] = pointer;
      this.head = pointer;
      this.forward[pointer] = oldHead;
      return this;
    };
    LRUCache.prototype.set = function(key, value) {
      var pointer = this.items[key];
      if (typeof pointer !== "undefined") {
        this.splayOnTop(pointer);
        this.V[pointer] = value;
        return;
      }
      if (this.size < this.capacity) {
        pointer = this.size++;
      } else {
        pointer = this.tail;
        this.tail = this.backward[pointer];
        delete this.items[this.K[pointer]];
      }
      this.items[key] = pointer;
      this.K[pointer] = key;
      this.V[pointer] = value;
      this.forward[pointer] = this.head;
      this.backward[this.head] = pointer;
      this.head = pointer;
    };
    LRUCache.prototype.setpop = function(key, value) {
      var oldValue = null;
      var oldKey = null;
      var pointer = this.items[key];
      if (typeof pointer !== "undefined") {
        this.splayOnTop(pointer);
        oldValue = this.V[pointer];
        this.V[pointer] = value;
        return { evicted: false, key, value: oldValue };
      }
      if (this.size < this.capacity) {
        pointer = this.size++;
      } else {
        pointer = this.tail;
        this.tail = this.backward[pointer];
        oldValue = this.V[pointer];
        oldKey = this.K[pointer];
        delete this.items[oldKey];
      }
      this.items[key] = pointer;
      this.K[pointer] = key;
      this.V[pointer] = value;
      this.forward[pointer] = this.head;
      this.backward[this.head] = pointer;
      this.head = pointer;
      if (oldKey) {
        return { evicted: true, key: oldKey, value: oldValue };
      } else {
        return null;
      }
    };
    LRUCache.prototype.has = function(key) {
      return key in this.items;
    };
    LRUCache.prototype.get = function(key) {
      var pointer = this.items[key];
      if (typeof pointer === "undefined")
        return;
      this.splayOnTop(pointer);
      return this.V[pointer];
    };
    LRUCache.prototype.peek = function(key) {
      var pointer = this.items[key];
      if (typeof pointer === "undefined")
        return;
      return this.V[pointer];
    };
    LRUCache.prototype.forEach = function(callback, scope) {
      scope = arguments.length > 1 ? scope : this;
      var i = 0, l = this.size;
      var pointer = this.head, keys = this.K, values = this.V, forward = this.forward;
      while (i < l) {
        callback.call(scope, values[pointer], keys[pointer], this);
        pointer = forward[pointer];
        i++;
      }
    };
    LRUCache.prototype.keys = function() {
      var i = 0, l = this.size;
      var pointer = this.head, keys = this.K, forward = this.forward;
      return new Iterator(function() {
        if (i >= l)
          return { done: true };
        var key = keys[pointer];
        i++;
        if (i < l)
          pointer = forward[pointer];
        return {
          done: false,
          value: key
        };
      });
    };
    LRUCache.prototype.values = function() {
      var i = 0, l = this.size;
      var pointer = this.head, values = this.V, forward = this.forward;
      return new Iterator(function() {
        if (i >= l)
          return { done: true };
        var value = values[pointer];
        i++;
        if (i < l)
          pointer = forward[pointer];
        return {
          done: false,
          value
        };
      });
    };
    LRUCache.prototype.entries = function() {
      var i = 0, l = this.size;
      var pointer = this.head, keys = this.K, values = this.V, forward = this.forward;
      return new Iterator(function() {
        if (i >= l)
          return { done: true };
        var key = keys[pointer], value = values[pointer];
        i++;
        if (i < l)
          pointer = forward[pointer];
        return {
          done: false,
          value: [key, value]
        };
      });
    };
    if (typeof Symbol !== "undefined")
      LRUCache.prototype[Symbol.iterator] = LRUCache.prototype.entries;
    LRUCache.prototype.inspect = function() {
      var proxy = /* @__PURE__ */ new Map();
      var iterator = this.entries(), step;
      while (step = iterator.next(), !step.done)
        proxy.set(step.value[0], step.value[1]);
      Object.defineProperty(proxy, "constructor", {
        value: LRUCache,
        enumerable: false
      });
      return proxy;
    };
    if (typeof Symbol !== "undefined")
      LRUCache.prototype[Symbol.for("nodejs.util.inspect.custom")] = LRUCache.prototype.inspect;
    LRUCache.from = function(iterable, Keys, Values, capacity) {
      if (arguments.length < 2) {
        capacity = iterables.guessLength(iterable);
        if (typeof capacity !== "number")
          throw new Error("mnemonist/lru-cache.from: could not guess iterable length. Please provide desired capacity as last argument.");
      } else if (arguments.length === 2) {
        capacity = Keys;
        Keys = null;
        Values = null;
      }
      var cache = new LRUCache(Keys, Values, capacity);
      forEach(iterable, function(value, key) {
        cache.set(key, value);
      });
      return cache;
    };
    module.exports = LRUCache;
  }
});

// node_modules/mnemonist/lru-map.js
var require_lru_map = __commonJS({
  "node_modules/mnemonist/lru-map.js"(exports, module) {
    var LRUCache = require_lru_cache();
    var forEach = require_foreach();
    var typed = require_typed_arrays();
    var iterables = require_iterables();
    function LRUMap(Keys, Values, capacity) {
      if (arguments.length < 2) {
        capacity = Keys;
        Keys = null;
        Values = null;
      }
      this.capacity = capacity;
      if (typeof this.capacity !== "number" || this.capacity <= 0)
        throw new Error("mnemonist/lru-map: capacity should be positive number.");
      else if (!isFinite(this.capacity) || Math.floor(this.capacity) !== this.capacity)
        throw new Error("mnemonist/lru-map: capacity should be a finite positive integer.");
      var PointerArray = typed.getPointerArray(capacity);
      this.forward = new PointerArray(capacity);
      this.backward = new PointerArray(capacity);
      this.K = typeof Keys === "function" ? new Keys(capacity) : new Array(capacity);
      this.V = typeof Values === "function" ? new Values(capacity) : new Array(capacity);
      this.size = 0;
      this.head = 0;
      this.tail = 0;
      this.items = /* @__PURE__ */ new Map();
    }
    LRUMap.prototype.clear = function() {
      this.size = 0;
      this.head = 0;
      this.tail = 0;
      this.items.clear();
    };
    LRUMap.prototype.set = function(key, value) {
      var pointer = this.items.get(key);
      if (typeof pointer !== "undefined") {
        this.splayOnTop(pointer);
        this.V[pointer] = value;
        return;
      }
      if (this.size < this.capacity) {
        pointer = this.size++;
      } else {
        pointer = this.tail;
        this.tail = this.backward[pointer];
        this.items.delete(this.K[pointer]);
      }
      this.items.set(key, pointer);
      this.K[pointer] = key;
      this.V[pointer] = value;
      this.forward[pointer] = this.head;
      this.backward[this.head] = pointer;
      this.head = pointer;
    };
    LRUMap.prototype.setpop = function(key, value) {
      var oldValue = null;
      var oldKey = null;
      var pointer = this.items.get(key);
      if (typeof pointer !== "undefined") {
        this.splayOnTop(pointer);
        oldValue = this.V[pointer];
        this.V[pointer] = value;
        return { evicted: false, key, value: oldValue };
      }
      if (this.size < this.capacity) {
        pointer = this.size++;
      } else {
        pointer = this.tail;
        this.tail = this.backward[pointer];
        oldValue = this.V[pointer];
        oldKey = this.K[pointer];
        this.items.delete(oldKey);
      }
      this.items.set(key, pointer);
      this.K[pointer] = key;
      this.V[pointer] = value;
      this.forward[pointer] = this.head;
      this.backward[this.head] = pointer;
      this.head = pointer;
      if (oldKey) {
        return { evicted: true, key: oldKey, value: oldValue };
      } else {
        return null;
      }
    };
    LRUMap.prototype.has = function(key) {
      return this.items.has(key);
    };
    LRUMap.prototype.get = function(key) {
      var pointer = this.items.get(key);
      if (typeof pointer === "undefined")
        return;
      this.splayOnTop(pointer);
      return this.V[pointer];
    };
    LRUMap.prototype.peek = function(key) {
      var pointer = this.items.get(key);
      if (typeof pointer === "undefined")
        return;
      return this.V[pointer];
    };
    LRUMap.prototype.splayOnTop = LRUCache.prototype.splayOnTop;
    LRUMap.prototype.forEach = LRUCache.prototype.forEach;
    LRUMap.prototype.keys = LRUCache.prototype.keys;
    LRUMap.prototype.values = LRUCache.prototype.values;
    LRUMap.prototype.entries = LRUCache.prototype.entries;
    if (typeof Symbol !== "undefined")
      LRUMap.prototype[Symbol.iterator] = LRUMap.prototype.entries;
    LRUMap.prototype.inspect = LRUCache.prototype.inspect;
    LRUMap.from = function(iterable, Keys, Values, capacity) {
      if (arguments.length < 2) {
        capacity = iterables.guessLength(iterable);
        if (typeof capacity !== "number")
          throw new Error("mnemonist/lru-cache.from: could not guess iterable length. Please provide desired capacity as last argument.");
      } else if (arguments.length === 2) {
        capacity = Keys;
        Keys = null;
        Values = null;
      }
      var cache = new LRUMap(Keys, Values, capacity);
      forEach(iterable, function(value, key) {
        cache.set(key, value);
      });
      return cache;
    };
    module.exports = LRUMap;
  }
});

// node_modules/mnemonist/lru-map-with-delete.js
var require_lru_map_with_delete = __commonJS({
  "node_modules/mnemonist/lru-map-with-delete.js"(exports, module) {
    var LRUMap = require_lru_map();
    var forEach = require_foreach();
    var typed = require_typed_arrays();
    var iterables = require_iterables();
    function LRUMapWithDelete(Keys, Values, capacity) {
      if (arguments.length < 2) {
        LRUMap.call(this, Keys);
      } else {
        LRUMap.call(this, Keys, Values, capacity);
      }
      var PointerArray = typed.getPointerArray(this.capacity);
      this.deleted = new PointerArray(this.capacity);
      this.deletedSize = 0;
    }
    for (k in LRUMap.prototype)
      LRUMapWithDelete.prototype[k] = LRUMap.prototype[k];
    var k;
    if (typeof Symbol !== "undefined")
      LRUMapWithDelete.prototype[Symbol.iterator] = LRUMap.prototype[Symbol.iterator];
    LRUMapWithDelete.prototype.clear = function() {
      LRUMap.prototype.clear.call(this);
      this.deletedSize = 0;
    };
    LRUMapWithDelete.prototype.set = function(key, value) {
      var pointer = this.items.get(key);
      if (typeof pointer !== "undefined") {
        this.splayOnTop(pointer);
        this.V[pointer] = value;
        return;
      }
      if (this.size < this.capacity) {
        if (this.deletedSize > 0) {
          pointer = this.deleted[--this.deletedSize];
        } else {
          pointer = this.size;
        }
        this.size++;
      } else {
        pointer = this.tail;
        this.tail = this.backward[pointer];
        this.items.delete(this.K[pointer]);
      }
      this.items.set(key, pointer);
      this.K[pointer] = key;
      this.V[pointer] = value;
      this.forward[pointer] = this.head;
      this.backward[this.head] = pointer;
      this.head = pointer;
    };
    LRUMapWithDelete.prototype.setpop = function(key, value) {
      var oldValue = null;
      var oldKey = null;
      var pointer = this.items.get(key);
      if (typeof pointer !== "undefined") {
        this.splayOnTop(pointer);
        oldValue = this.V[pointer];
        this.V[pointer] = value;
        return { evicted: false, key, value: oldValue };
      }
      if (this.size < this.capacity) {
        if (this.deletedSize > 0) {
          pointer = this.deleted[--this.deletedSize];
        } else {
          pointer = this.size;
        }
        this.size++;
      } else {
        pointer = this.tail;
        this.tail = this.backward[pointer];
        oldValue = this.V[pointer];
        oldKey = this.K[pointer];
        this.items.delete(oldKey);
      }
      this.items.set(key, pointer);
      this.K[pointer] = key;
      this.V[pointer] = value;
      this.forward[pointer] = this.head;
      this.backward[this.head] = pointer;
      this.head = pointer;
      if (oldKey) {
        return { evicted: true, key: oldKey, value: oldValue };
      } else {
        return null;
      }
    };
    LRUMapWithDelete.prototype.delete = function(key) {
      var pointer = this.items.get(key);
      if (typeof pointer === "undefined") {
        return false;
      }
      this.items.delete(key);
      if (this.size === 1) {
        this.size = 0;
        this.head = 0;
        this.tail = 0;
        this.deletedSize = 0;
        return true;
      }
      var previous = this.backward[pointer], next = this.forward[pointer];
      if (this.head === pointer) {
        this.head = next;
      }
      if (this.tail === pointer) {
        this.tail = previous;
      }
      this.forward[previous] = next;
      this.backward[next] = previous;
      this.size--;
      this.deleted[this.deletedSize++] = pointer;
      return true;
    };
    LRUMapWithDelete.prototype.remove = function(key, missing = void 0) {
      var pointer = this.items.get(key);
      if (typeof pointer === "undefined") {
        return missing;
      }
      var dead = this.V[pointer];
      this.items.delete(key);
      if (this.size === 1) {
        this.size = 0;
        this.head = 0;
        this.tail = 0;
        this.deletedSize = 0;
        return dead;
      }
      var previous = this.backward[pointer], next = this.forward[pointer];
      if (this.head === pointer) {
        this.head = next;
      }
      if (this.tail === pointer) {
        this.tail = previous;
      }
      this.forward[previous] = next;
      this.backward[next] = previous;
      this.size--;
      this.deleted[this.deletedSize++] = pointer;
      return dead;
    };
    LRUMapWithDelete.from = function(iterable, Keys, Values, capacity) {
      if (arguments.length < 2) {
        capacity = iterables.guessLength(iterable);
        if (typeof capacity !== "number")
          throw new Error("mnemonist/lru-map.from: could not guess iterable length. Please provide desired capacity as last argument.");
      } else if (arguments.length === 2) {
        capacity = Keys;
        Keys = null;
        Values = null;
      }
      var cache = new LRUMapWithDelete(Keys, Values, capacity);
      forEach(iterable, function(value, key) {
        cache.set(key, value);
      });
      return cache;
    };
    module.exports = LRUMapWithDelete;
  }
});

// node_modules/ink/build/worker/worker-entry.js
import process7 from "node:process";

// node_modules/ink/build/worker/render-worker.js
import fs3 from "node:fs";
import process6 from "node:process";

// node_modules/ansi-escapes/base.js
var base_exports = {};
__export(base_exports, {
  beep: () => beep,
  clearScreen: () => clearScreen,
  clearTerminal: () => clearTerminal,
  cursorBackward: () => cursorBackward,
  cursorDown: () => cursorDown,
  cursorForward: () => cursorForward,
  cursorGetPosition: () => cursorGetPosition,
  cursorHide: () => cursorHide,
  cursorLeft: () => cursorLeft,
  cursorMove: () => cursorMove,
  cursorNextLine: () => cursorNextLine,
  cursorPrevLine: () => cursorPrevLine,
  cursorRestorePosition: () => cursorRestorePosition,
  cursorSavePosition: () => cursorSavePosition,
  cursorShow: () => cursorShow,
  cursorTo: () => cursorTo,
  cursorUp: () => cursorUp,
  enterAlternativeScreen: () => enterAlternativeScreen,
  eraseDown: () => eraseDown,
  eraseEndLine: () => eraseEndLine,
  eraseLine: () => eraseLine,
  eraseLines: () => eraseLines,
  eraseScreen: () => eraseScreen,
  eraseStartLine: () => eraseStartLine,
  eraseUp: () => eraseUp,
  exitAlternativeScreen: () => exitAlternativeScreen,
  iTerm: () => iTerm,
  image: () => image,
  link: () => link,
  scrollDown: () => scrollDown,
  scrollUp: () => scrollUp
});
import process from "node:process";

// node_modules/environment/index.js
var isBrowser = globalThis.window?.document !== void 0;
var isNode = globalThis.process?.versions?.node !== void 0;
var isBun = globalThis.process?.versions?.bun !== void 0;
var isDeno = globalThis.Deno?.version?.deno !== void 0;
var isElectron = globalThis.process?.versions?.electron !== void 0;
var isJsDom = globalThis.navigator?.userAgent?.includes("jsdom") === true;
var isWebWorker = typeof WorkerGlobalScope !== "undefined" && globalThis instanceof WorkerGlobalScope;
var isDedicatedWorker = typeof DedicatedWorkerGlobalScope !== "undefined" && globalThis instanceof DedicatedWorkerGlobalScope;
var isSharedWorker = typeof SharedWorkerGlobalScope !== "undefined" && globalThis instanceof SharedWorkerGlobalScope;
var isServiceWorker = typeof ServiceWorkerGlobalScope !== "undefined" && globalThis instanceof ServiceWorkerGlobalScope;
var platform = globalThis.navigator?.userAgentData?.platform;
var isMacOs = platform === "macOS" || globalThis.navigator?.platform === "MacIntel" || globalThis.navigator?.userAgent?.includes(" Mac ") === true || globalThis.process?.platform === "darwin";
var isWindows = platform === "Windows" || globalThis.navigator?.platform === "Win32" || globalThis.process?.platform === "win32";
var isLinux = platform === "Linux" || globalThis.navigator?.platform?.startsWith("Linux") === true || globalThis.navigator?.userAgent?.includes(" Linux ") === true || globalThis.process?.platform === "linux";
var isIos = platform === "iOS" || globalThis.navigator?.platform === "MacIntel" && globalThis.navigator?.maxTouchPoints > 1 || /iPad|iPhone|iPod/.test(globalThis.navigator?.platform);
var isAndroid = platform === "Android" || globalThis.navigator?.platform === "Android" || globalThis.navigator?.userAgent?.includes(" Android ") === true || globalThis.process?.platform === "android";

// node_modules/ansi-escapes/base.js
var ESC = "\x1B[";
var OSC = "\x1B]";
var BEL = "\x07";
var SEP = ";";
var isTerminalApp = !isBrowser && process.env.TERM_PROGRAM === "Apple_Terminal";
var isWindows2 = !isBrowser && process.platform === "win32";
var cwdFunction = isBrowser ? () => {
  throw new Error("`process.cwd()` only works in Node.js, not the browser.");
} : process.cwd;
var cursorTo = (x, y) => {
  if (typeof x !== "number") {
    throw new TypeError("The `x` argument is required");
  }
  if (typeof y !== "number") {
    return ESC + (x + 1) + "G";
  }
  return ESC + (y + 1) + SEP + (x + 1) + "H";
};
var cursorMove = (x, y) => {
  if (typeof x !== "number") {
    throw new TypeError("The `x` argument is required");
  }
  let returnValue = "";
  if (x < 0) {
    returnValue += ESC + -x + "D";
  } else if (x > 0) {
    returnValue += ESC + x + "C";
  }
  if (y < 0) {
    returnValue += ESC + -y + "A";
  } else if (y > 0) {
    returnValue += ESC + y + "B";
  }
  return returnValue;
};
var cursorUp = (count = 1) => ESC + count + "A";
var cursorDown = (count = 1) => ESC + count + "B";
var cursorForward = (count = 1) => ESC + count + "C";
var cursorBackward = (count = 1) => ESC + count + "D";
var cursorLeft = ESC + "G";
var cursorSavePosition = isTerminalApp ? "\x1B7" : ESC + "s";
var cursorRestorePosition = isTerminalApp ? "\x1B8" : ESC + "u";
var cursorGetPosition = ESC + "6n";
var cursorNextLine = ESC + "E";
var cursorPrevLine = ESC + "F";
var cursorHide = ESC + "?25l";
var cursorShow = ESC + "?25h";
var eraseLines = (count) => {
  let clear = "";
  for (let i = 0; i < count; i++) {
    clear += eraseLine + (i < count - 1 ? cursorUp() : "");
  }
  if (count) {
    clear += cursorLeft;
  }
  return clear;
};
var eraseEndLine = ESC + "K";
var eraseStartLine = ESC + "1K";
var eraseLine = ESC + "2K";
var eraseDown = ESC + "J";
var eraseUp = ESC + "1J";
var eraseScreen = ESC + "2J";
var scrollUp = ESC + "S";
var scrollDown = ESC + "T";
var clearScreen = "\x1Bc";
var clearTerminal = isWindows2 ? `${eraseScreen}${ESC}0f` : `${eraseScreen}${ESC}3J${ESC}H`;
var enterAlternativeScreen = ESC + "?1049h";
var exitAlternativeScreen = ESC + "?1049l";
var beep = BEL;
var link = (text, url) => [
  OSC,
  "8",
  SEP,
  SEP,
  url,
  BEL,
  text,
  OSC,
  "8",
  SEP,
  SEP,
  BEL
].join("");
var image = (data, options = {}) => {
  let returnValue = `${OSC}1337;File=inline=1`;
  if (options.width) {
    returnValue += `;width=${options.width}`;
  }
  if (options.height) {
    returnValue += `;height=${options.height}`;
  }
  if (options.preserveAspectRatio === false) {
    returnValue += ";preserveAspectRatio=0";
  }
  return returnValue + ":" + Buffer.from(data).toString("base64") + BEL;
};
var iTerm = {
  setCwd: (cwd = cwdFunction()) => `${OSC}50;CurrentDir=${cwd}${BEL}`,
  annotation(message, options = {}) {
    let returnValue = `${OSC}1337;`;
    const hasX = options.x !== void 0;
    const hasY = options.y !== void 0;
    if ((hasX || hasY) && !(hasX && hasY && options.length !== void 0)) {
      throw new Error("`x`, `y` and `length` must be defined when `x` or `y` is defined");
    }
    message = message.replaceAll("|", "");
    returnValue += options.isHidden ? "AddHiddenAnnotation=" : "AddAnnotation=";
    if (options.length > 0) {
      returnValue += (hasX ? [message, options.length, options.x, options.y] : [options.length, message]).join("|");
    } else {
      returnValue += message;
    }
    return returnValue + BEL;
  }
};

// node_modules/ink/build/debug-log.js
import fs from "node:fs";
import path from "node:path";
import process2 from "node:process";
var debugLogEnabled = false;
var isFirstRun = true;
var logFilePath = path.join(process2.cwd(), "debug.log");
var logStream;
var debugLog = (message) => {
  if (!debugLogEnabled) {
    return;
  }
  if (isFirstRun) {
    try {
      logStream = fs.createWriteStream(logFilePath, { flags: "w" });
    } catch (error) {
      process2.stderr.write(`[debug-log] Failed to start writing to debug file ${logFilePath} in debugLog: ${String(error)}
`);
    }
    isFirstRun = false;
  }
  if (logStream) {
    try {
      logStream.write(message + "\n");
    } catch (error) {
      process2.stderr.write(`[debug-log] Failed to write to debug file ${logFilePath} in debugLog: ${String(error)}
`);
    }
  }
};
var clearDebugLog = () => {
  if (!debugLogEnabled) {
    return;
  }
  if (logStream) {
    logStream.end();
  }
  try {
    logStream = fs.createWriteStream(logFilePath, { flags: "w" });
  } catch (error) {
    process2.stderr.write(`[debug-log] Failed to start writing to debug file ${logFilePath} in clearDebugLog: ${String(error)}
`);
  }
};

// node_modules/get-east-asian-width/lookup.js
function isFullWidth(x) {
  return x === 12288 || x >= 65281 && x <= 65376 || x >= 65504 && x <= 65510;
}
function isWide(x) {
  return x >= 4352 && x <= 4447 || x === 8986 || x === 8987 || x === 9001 || x === 9002 || x >= 9193 && x <= 9196 || x === 9200 || x === 9203 || x === 9725 || x === 9726 || x === 9748 || x === 9749 || x >= 9776 && x <= 9783 || x >= 9800 && x <= 9811 || x === 9855 || x >= 9866 && x <= 9871 || x === 9875 || x === 9889 || x === 9898 || x === 9899 || x === 9917 || x === 9918 || x === 9924 || x === 9925 || x === 9934 || x === 9940 || x === 9962 || x === 9970 || x === 9971 || x === 9973 || x === 9978 || x === 9981 || x === 9989 || x === 9994 || x === 9995 || x === 10024 || x === 10060 || x === 10062 || x >= 10067 && x <= 10069 || x === 10071 || x >= 10133 && x <= 10135 || x === 10160 || x === 10175 || x === 11035 || x === 11036 || x === 11088 || x === 11093 || x >= 11904 && x <= 11929 || x >= 11931 && x <= 12019 || x >= 12032 && x <= 12245 || x >= 12272 && x <= 12287 || x >= 12289 && x <= 12350 || x >= 12353 && x <= 12438 || x >= 12441 && x <= 12543 || x >= 12549 && x <= 12591 || x >= 12593 && x <= 12686 || x >= 12688 && x <= 12773 || x >= 12783 && x <= 12830 || x >= 12832 && x <= 12871 || x >= 12880 && x <= 42124 || x >= 42128 && x <= 42182 || x >= 43360 && x <= 43388 || x >= 44032 && x <= 55203 || x >= 63744 && x <= 64255 || x >= 65040 && x <= 65049 || x >= 65072 && x <= 65106 || x >= 65108 && x <= 65126 || x >= 65128 && x <= 65131 || x >= 94176 && x <= 94180 || x >= 94192 && x <= 94198 || x >= 94208 && x <= 101589 || x >= 101631 && x <= 101662 || x >= 101760 && x <= 101874 || x >= 110576 && x <= 110579 || x >= 110581 && x <= 110587 || x === 110589 || x === 110590 || x >= 110592 && x <= 110882 || x === 110898 || x >= 110928 && x <= 110930 || x === 110933 || x >= 110948 && x <= 110951 || x >= 110960 && x <= 111355 || x >= 119552 && x <= 119638 || x >= 119648 && x <= 119670 || x === 126980 || x === 127183 || x === 127374 || x >= 127377 && x <= 127386 || x >= 127488 && x <= 127490 || x >= 127504 && x <= 127547 || x >= 127552 && x <= 127560 || x === 127568 || x === 127569 || x >= 127584 && x <= 127589 || x >= 127744 && x <= 127776 || x >= 127789 && x <= 127797 || x >= 127799 && x <= 127868 || x >= 127870 && x <= 127891 || x >= 127904 && x <= 127946 || x >= 127951 && x <= 127955 || x >= 127968 && x <= 127984 || x === 127988 || x >= 127992 && x <= 128062 || x === 128064 || x >= 128066 && x <= 128252 || x >= 128255 && x <= 128317 || x >= 128331 && x <= 128334 || x >= 128336 && x <= 128359 || x === 128378 || x === 128405 || x === 128406 || x === 128420 || x >= 128507 && x <= 128591 || x >= 128640 && x <= 128709 || x === 128716 || x >= 128720 && x <= 128722 || x >= 128725 && x <= 128728 || x >= 128732 && x <= 128735 || x === 128747 || x === 128748 || x >= 128756 && x <= 128764 || x >= 128992 && x <= 129003 || x === 129008 || x >= 129292 && x <= 129338 || x >= 129340 && x <= 129349 || x >= 129351 && x <= 129535 || x >= 129648 && x <= 129660 || x >= 129664 && x <= 129674 || x >= 129678 && x <= 129734 || x === 129736 || x >= 129741 && x <= 129756 || x >= 129759 && x <= 129770 || x >= 129775 && x <= 129784 || x >= 131072 && x <= 196605 || x >= 196608 && x <= 262141;
}

// node_modules/ink/node_modules/is-fullwidth-code-point/index.js
function isFullwidthCodePoint(codePoint) {
  if (!Number.isInteger(codePoint)) {
    return false;
  }
  return isFullWidth(codePoint) || isWide(codePoint);
}

// node_modules/ink/node_modules/ansi-styles/index.js
var ANSI_BACKGROUND_OFFSET = 10;
var wrapAnsi16 = (offset = 0) => (code) => `\x1B[${code + offset}m`;
var wrapAnsi256 = (offset = 0) => (code) => `\x1B[${38 + offset};5;${code}m`;
var wrapAnsi16m = (offset = 0) => (red, green, blue) => `\x1B[${38 + offset};2;${red};${green};${blue}m`;
var styles = {
  modifier: {
    reset: [0, 0],
    // 21 isn't widely supported and 22 does the same thing
    bold: [1, 22],
    dim: [2, 22],
    italic: [3, 23],
    underline: [4, 24],
    overline: [53, 55],
    inverse: [7, 27],
    hidden: [8, 28],
    strikethrough: [9, 29]
  },
  color: {
    black: [30, 39],
    red: [31, 39],
    green: [32, 39],
    yellow: [33, 39],
    blue: [34, 39],
    magenta: [35, 39],
    cyan: [36, 39],
    white: [37, 39],
    // Bright color
    blackBright: [90, 39],
    gray: [90, 39],
    // Alias of `blackBright`
    grey: [90, 39],
    // Alias of `blackBright`
    redBright: [91, 39],
    greenBright: [92, 39],
    yellowBright: [93, 39],
    blueBright: [94, 39],
    magentaBright: [95, 39],
    cyanBright: [96, 39],
    whiteBright: [97, 39]
  },
  bgColor: {
    bgBlack: [40, 49],
    bgRed: [41, 49],
    bgGreen: [42, 49],
    bgYellow: [43, 49],
    bgBlue: [44, 49],
    bgMagenta: [45, 49],
    bgCyan: [46, 49],
    bgWhite: [47, 49],
    // Bright color
    bgBlackBright: [100, 49],
    bgGray: [100, 49],
    // Alias of `bgBlackBright`
    bgGrey: [100, 49],
    // Alias of `bgBlackBright`
    bgRedBright: [101, 49],
    bgGreenBright: [102, 49],
    bgYellowBright: [103, 49],
    bgBlueBright: [104, 49],
    bgMagentaBright: [105, 49],
    bgCyanBright: [106, 49],
    bgWhiteBright: [107, 49]
  }
};
var modifierNames = Object.keys(styles.modifier);
var foregroundColorNames = Object.keys(styles.color);
var backgroundColorNames = Object.keys(styles.bgColor);
var colorNames = [...foregroundColorNames, ...backgroundColorNames];
function assembleStyles() {
  const codes = /* @__PURE__ */ new Map();
  for (const [groupName, group] of Object.entries(styles)) {
    for (const [styleName, style] of Object.entries(group)) {
      styles[styleName] = {
        open: `\x1B[${style[0]}m`,
        close: `\x1B[${style[1]}m`
      };
      group[styleName] = styles[styleName];
      codes.set(style[0], style[1]);
    }
    Object.defineProperty(styles, groupName, {
      value: group,
      enumerable: false
    });
  }
  Object.defineProperty(styles, "codes", {
    value: codes,
    enumerable: false
  });
  styles.color.close = "\x1B[39m";
  styles.bgColor.close = "\x1B[49m";
  styles.color.ansi = wrapAnsi16();
  styles.color.ansi256 = wrapAnsi256();
  styles.color.ansi16m = wrapAnsi16m();
  styles.bgColor.ansi = wrapAnsi16(ANSI_BACKGROUND_OFFSET);
  styles.bgColor.ansi256 = wrapAnsi256(ANSI_BACKGROUND_OFFSET);
  styles.bgColor.ansi16m = wrapAnsi16m(ANSI_BACKGROUND_OFFSET);
  Object.defineProperties(styles, {
    rgbToAnsi256: {
      value(red, green, blue) {
        if (red === green && green === blue) {
          if (red < 8) {
            return 16;
          }
          if (red > 248) {
            return 231;
          }
          return Math.round((red - 8) / 247 * 24) + 232;
        }
        return 16 + 36 * Math.round(red / 255 * 5) + 6 * Math.round(green / 255 * 5) + Math.round(blue / 255 * 5);
      },
      enumerable: false
    },
    hexToRgb: {
      value(hex) {
        const matches = /[a-f\d]{6}|[a-f\d]{3}/i.exec(hex.toString(16));
        if (!matches) {
          return [0, 0, 0];
        }
        let [colorString] = matches;
        if (colorString.length === 3) {
          colorString = [...colorString].map((character) => character + character).join("");
        }
        const integer = Number.parseInt(colorString, 16);
        return [
          /* eslint-disable no-bitwise */
          integer >> 16 & 255,
          integer >> 8 & 255,
          integer & 255
          /* eslint-enable no-bitwise */
        ];
      },
      enumerable: false
    },
    hexToAnsi256: {
      value: (hex) => styles.rgbToAnsi256(...styles.hexToRgb(hex)),
      enumerable: false
    },
    ansi256ToAnsi: {
      value(code) {
        if (code < 8) {
          return 30 + code;
        }
        if (code < 16) {
          return 90 + (code - 8);
        }
        let red;
        let green;
        let blue;
        if (code >= 232) {
          red = ((code - 232) * 10 + 8) / 255;
          green = red;
          blue = red;
        } else {
          code -= 16;
          const remainder = code % 36;
          red = Math.floor(code / 36) / 5;
          green = Math.floor(remainder / 6) / 5;
          blue = remainder % 6 / 5;
        }
        const value = Math.max(red, green, blue) * 2;
        if (value === 0) {
          return 30;
        }
        let result = 30 + (Math.round(blue) << 2 | Math.round(green) << 1 | Math.round(red));
        if (value === 2) {
          result += 60;
        }
        return result;
      },
      enumerable: false
    },
    rgbToAnsi: {
      value: (red, green, blue) => styles.ansi256ToAnsi(styles.rgbToAnsi256(red, green, blue)),
      enumerable: false
    },
    hexToAnsi: {
      value: (hex) => styles.ansi256ToAnsi(styles.hexToAnsi256(hex)),
      enumerable: false
    }
  });
  return styles;
}
var ansiStyles = assembleStyles();
var ansi_styles_default = ansiStyles;

// node_modules/ink/build/styled-line.js
var OFFSET_MASK = 1073741823;
var FULL_WIDTH_FLAG = 1073741824;
var StyledLine = class _StyledLine {
  static empty(length) {
    if (length <= 0) {
      return new _StyledLine();
    }
    const cached = _StyledLine.emptyCache.get(length);
    if (cached) {
      return cached.clone();
    }
    const line = new _StyledLine();
    line.length = length;
    line.text = " ".repeat(length);
    line.charData = Array.from({ length });
    for (let i = 0; i < length; i++) {
      line.charData[i] = i;
    }
    line.spans = [{ length, formatFlags: 0 }];
    line._cachedTrimmedLength = 0;
    if (_StyledLine.emptyCache.size > 100) {
      _StyledLine.emptyCache.clear();
    }
    Object.freeze(line.spans[0]);
    Object.freeze(line.spans);
    Object.freeze(line);
    _StyledLine.emptyCache.set(length, line);
    return line.clone();
  }
  static legacyCreateStyledLine(values = [], spans = []) {
    const line = new _StyledLine();
    line.applyValuesAndSpans(values, spans);
    return line;
  }
  static emptyCache = /* @__PURE__ */ new Map();
  length;
  text;
  charData;
  spans;
  _cachedTrimmedLength;
  constructor() {
    this.length = 0;
  }
  getValue(index) {
    if (this.text === void 0 || index < 0 || index >= this.length)
      return "";
    const start = this.charData[index] & OFFSET_MASK;
    const end = index + 1 < this.length ? this.charData[index + 1] & OFFSET_MASK : this.text.length;
    return this.text.slice(start, end);
  }
  getSpan(index) {
    if (this.spans === void 0 || index < 0 || index >= this.length)
      return void 0;
    let current = 0;
    for (const span of this.spans) {
      if (index < current + span.length)
        return span;
      current += span.length;
    }
    return void 0;
  }
  getFullWidth(index) {
    if (this.charData === void 0 || index < 0 || index >= this.length)
      return false;
    return (this.charData[index] & FULL_WIDTH_FLAG) !== 0;
  }
  hasStyles(index) {
    const span = this.getSpan(index);
    if (!span)
      return false;
    return (span.formatFlags & ~FULL_WIDTH_MASK) !== 0 || span.fgColor !== void 0 || span.bgColor !== void 0 || span.link !== void 0;
  }
  getFormatFlags(index) {
    let flags = this.getSpan(index)?.formatFlags ?? 0;
    if (this.getFullWidth(index)) {
      flags |= FULL_WIDTH_MASK;
    }
    return flags;
  }
  getFgColor(index) {
    return this.getSpan(index)?.fgColor;
  }
  getBgColor(index) {
    return this.getSpan(index)?.bgColor;
  }
  getLink(index) {
    return this.getSpan(index)?.link;
  }
  setInverted(index, inverted) {
    if (index < 0 || index >= this.length)
      return;
    this._cachedTrimmedLength = void 0;
    this.ensureInitialized();
    this.splitSpansAt(index);
    this.splitSpansAt(index + 1);
    let current = 0;
    for (const span of this.spans) {
      if (current === index && span.length === 1) {
        if (inverted) {
          span.formatFlags |= INVERSE_MASK;
        } else {
          span.formatFlags &= ~INVERSE_MASK;
        }
        break;
      }
      current += span.length;
    }
    this.mergeSpans();
  }
  setBackgroundColor(index, color) {
    if (index < 0 || index >= this.length)
      return;
    this._cachedTrimmedLength = void 0;
    this.ensureInitialized();
    this.splitSpansAt(index);
    this.splitSpansAt(index + 1);
    let current = 0;
    for (const span of this.spans) {
      if (current === index && span.length === 1) {
        span.bgColor = color;
        break;
      }
      current += span.length;
    }
    this.mergeSpans();
  }
  setForegroundColor(index, color) {
    if (index < 0 || index >= this.length)
      return;
    this._cachedTrimmedLength = void 0;
    this.ensureInitialized();
    this.splitSpansAt(index);
    this.splitSpansAt(index + 1);
    let current = 0;
    for (const span of this.spans) {
      if (current === index && span.length === 1) {
        span.fgColor = color;
        break;
      }
      current += span.length;
    }
    this.mergeSpans();
  }
  // eslint-disable-next-line max-params
  setChar(index, value, formatFlags, fgColor, bgColor, link2) {
    if (index < 0 || index >= this.length)
      return;
    this._cachedTrimmedLength = void 0;
    this.ensureInitialized();
    const isFullWidth2 = (formatFlags & FULL_WIDTH_MASK) !== 0;
    const cleanFormatFlags = formatFlags & ~FULL_WIDTH_MASK;
    const start = this.charData[index] & OFFSET_MASK;
    const end = index + 1 < this.length ? this.charData[index + 1] & OFFSET_MASK : this.text.length;
    const oldLen = end - start;
    const newLen = value.length;
    if (oldLen === newLen) {
      this.text = this.text.slice(0, start) + value + this.text.slice(end);
    } else {
      this.text = this.text.slice(0, start) + value + this.text.slice(end);
      const diff = newLen - oldLen;
      for (let i = index + 1; i < this.length; i++) {
        const data = this.charData[i];
        const oldOffset = data & OFFSET_MASK;
        const fw = data & FULL_WIDTH_FLAG;
        this.charData[i] = oldOffset + diff | fw;
      }
    }
    this.charData[index] = start | (isFullWidth2 ? FULL_WIDTH_FLAG : 0);
    this.splitSpansAt(index);
    this.splitSpansAt(index + 1);
    let current = 0;
    for (let i = 0; i < this.spans.length; i++) {
      const span = this.spans[i];
      if (current === index && span.length === 1) {
        this.spans[i] = {
          length: 1,
          formatFlags: cleanFormatFlags,
          fgColor,
          bgColor,
          link: link2
        };
        break;
      }
      current += span.length;
    }
    this.mergeSpans();
  }
  // eslint-disable-next-line max-params
  pushChar(value, formatFlags, fgColor, bgColor, link2) {
    this._cachedTrimmedLength = void 0;
    this.ensureInitialized();
    const isFullWidth2 = (formatFlags & FULL_WIDTH_MASK) !== 0;
    const cleanFormatFlags = formatFlags & ~FULL_WIDTH_MASK;
    const offset = this.text.length;
    this.text += value;
    this.charData.push(offset | (isFullWidth2 ? FULL_WIDTH_FLAG : 0));
    const lastSpan = this.spans.at(-1);
    if (lastSpan && lastSpan.formatFlags === cleanFormatFlags && lastSpan.fgColor === fgColor && lastSpan.bgColor === bgColor && lastSpan.link === link2) {
      lastSpan.length++;
    } else {
      this.spans.push({
        length: 1,
        formatFlags: cleanFormatFlags,
        fgColor,
        bgColor,
        link: link2
      });
    }
    this.length++;
  }
  clone() {
    if (this.charData === void 0)
      return new _StyledLine();
    const result = new _StyledLine();
    result.length = this.length;
    result.text = this.text;
    result.charData = [...this.charData];
    result.spans = this.spans.map((span) => ({ ...span }));
    result._cachedTrimmedLength = this._cachedTrimmedLength;
    return result;
  }
  slice(start, end) {
    if (this.charData === void 0)
      return new _StyledLine();
    const actualStart = Math.max(0, start);
    const actualEnd = end === void 0 ? this.length : Math.min(this.length, end);
    if (actualStart >= actualEnd)
      return new _StyledLine();
    if (actualStart === 0 && actualEnd === this.length) {
      return this.clone();
    }
    const result = new _StyledLine();
    result.length = actualEnd - actualStart;
    result.charData = Array.from({ length: result.length });
    const textStart = this.charData[actualStart] & OFFSET_MASK;
    const textEnd = actualEnd < this.length ? this.charData[actualEnd] & OFFSET_MASK : this.text.length;
    result.text = this.text.slice(textStart, textEnd);
    for (let i = 0; i < result.length; i++) {
      const oldData = this.charData[actualStart + i];
      const oldOffset = oldData & OFFSET_MASK;
      const fw = oldData & FULL_WIDTH_FLAG;
      result.charData[i] = oldOffset - textStart | fw;
    }
    const newSpans = [];
    let current = 0;
    for (const span of this.spans) {
      const spanStart = current;
      const spanEnd = current + span.length;
      const intersectStart = Math.max(actualStart, spanStart);
      const intersectEnd = Math.min(actualEnd, spanEnd);
      if (intersectStart < intersectEnd) {
        newSpans.push({
          ...span,
          length: intersectEnd - intersectStart
        });
      }
      current += span.length;
      if (current >= actualEnd)
        break;
    }
    result.spans = newSpans;
    result.mergeSpans();
    return result;
  }
  combine(...others) {
    if (others.length === 0)
      return this.clone();
    const allLines = [this, ...others].filter((l) => l.length > 0);
    if (allLines.length === 0)
      return new _StyledLine();
    if (allLines.length === 1)
      return allLines[0].clone();
    let totalChars = 0;
    for (const line of allLines) {
      totalChars += line.length;
    }
    const result = new _StyledLine();
    result.length = totalChars;
    result.text = allLines.map((l) => l.getText()).join("");
    result.charData = Array.from({ length: totalChars });
    let currentChar = 0;
    let currentOffset = 0;
    for (const line of allLines) {
      const lineCharData = line.charData;
      const lineText = line.getText();
      if (lineCharData) {
        for (let i = 0; i < line.length; i++) {
          const data = lineCharData[i];
          const offset = data & OFFSET_MASK;
          const fw = data & FULL_WIDTH_FLAG;
          result.charData[currentChar + i] = currentOffset + offset | fw;
        }
      } else {
        for (let i = 0; i < line.length; i++) {
          result.charData[currentChar + i] = currentOffset + i;
        }
      }
      currentChar += line.length;
      currentOffset += lineText.length;
    }
    result.spans = allLines.flatMap((l) => l.getSpans().map((s) => ({ ...s })));
    result.mergeSpans();
    return result;
  }
  getTrimmedLength() {
    if (this.length === 0)
      return 0;
    if (this.text === void 0 || this.charData === void 0)
      return 0;
    let currentIdx = this.length - 1;
    if (this.spans) {
      for (let s = this.spans.length - 1; s >= 0; s--) {
        const span = this.spans[s];
        const hasStyles = (span.formatFlags & ~FULL_WIDTH_MASK) !== 0 || span.fgColor !== void 0 || span.bgColor !== void 0 || span.link !== void 0;
        if (hasStyles) {
          return currentIdx + 1;
        }
        for (let i = 0; i < span.length; i++) {
          const start = this.charData[currentIdx] & OFFSET_MASK;
          const end = currentIdx + 1 < this.length ? this.charData[currentIdx + 1] & OFFSET_MASK : this.text.length;
          if (end - start !== 1 || this.text[start] !== " ") {
            return currentIdx + 1;
          }
          currentIdx--;
        }
      }
    }
    return 0;
  }
  trimEnd() {
    const trimmedLength = this.getTrimmedLength();
    if (trimmedLength === this.length)
      return this;
    if (trimmedLength === 0)
      return new _StyledLine();
    return this.slice(0, trimmedLength);
  }
  equals(other) {
    if (this.length !== other.length)
      return false;
    if (this.length === 0)
      return true;
    if (this.getText() !== other.getText())
      return false;
    const s1 = this.getSpans();
    const s2 = other.getSpans();
    if (s1.length !== s2.length)
      return false;
    for (let i = 0; i < s1.length; i++) {
      const sp1 = s1[i];
      const sp2 = s2[i];
      if (sp1.length !== sp2.length || sp1.formatFlags !== sp2.formatFlags || sp1.fgColor !== sp2.fgColor || sp1.bgColor !== sp2.bgColor || sp1.link !== sp2.link) {
        return false;
      }
    }
    const thisCharData = this.charData;
    const otherCharData = other.charData;
    if (thisCharData && otherCharData) {
      for (let i = 0; i < this.length; i++) {
        if (thisCharData[i] !== otherCharData[i])
          return false;
      }
    }
    return true;
  }
  getText() {
    return this.text ?? "";
  }
  getSpans() {
    return this.spans ?? [];
  }
  getValues() {
    return Array.from({ length: this.length }, (_, i) => this.getValue(i));
  }
  *[Symbol.iterator]() {
    if (this.length === 0)
      return;
    let currentSpanIdx = 0;
    let currentSpanPos = 0;
    const spans = this.getSpans();
    for (let i = 0; i < this.length; i++) {
      const span = spans[currentSpanIdx];
      const formatFlags = span ? span.formatFlags : 0;
      const isFullWidth2 = this.getFullWidth(i);
      yield {
        value: this.getValue(i),
        formatFlags: formatFlags | (isFullWidth2 ? FULL_WIDTH_MASK : 0),
        fgColor: span?.fgColor,
        bgColor: span?.bgColor,
        link: span?.link,
        fullWidth: isFullWidth2,
        hasStyles: (formatFlags & ~FULL_WIDTH_MASK) !== 0 || span?.fgColor !== void 0 || span?.bgColor !== void 0 || span?.link !== void 0
      };
      if (span) {
        currentSpanPos++;
        if (currentSpanPos >= span.length) {
          currentSpanIdx++;
          currentSpanPos = 0;
        }
      }
    }
  }
  ensureInitialized() {
    if (this.charData === void 0) {
      this.text = "";
      this.charData = Array.from({ length: this.length });
      this.spans = this.length > 0 ? [{ length: this.length, formatFlags: 0 }] : [];
      if (this.length > 0 && this.text.length === 0) {
        this.text = " ".repeat(this.length);
        for (let i = 0; i < this.length; i++) {
          this.charData[i] = i;
        }
      }
    }
  }
  applyValuesAndSpans(values, spans) {
    this._cachedTrimmedLength = void 0;
    const visibleChars = values.length;
    this.length = visibleChars;
    this.text = values.join("");
    this.charData = Array.from({ length: this.length });
    let currentOffset = 0;
    let spanIdx = 0;
    let spanPos = 0;
    for (let i = 0; i < visibleChars; i++) {
      const val = values[i];
      let isFullWidth2 = false;
      if (spans.length > 0 && spanIdx < spans.length) {
        const span = spans[spanIdx];
        if ((span.formatFlags & FULL_WIDTH_MASK) !== 0) {
          isFullWidth2 = true;
        }
        spanPos++;
        if (spanPos >= span.length) {
          spanIdx++;
          spanPos = 0;
        }
      }
      this.charData[i] = currentOffset | (isFullWidth2 ? FULL_WIDTH_FLAG : 0);
      currentOffset += val.length;
    }
    this.spans = spans.map((s) => ({
      ...s,
      formatFlags: s.formatFlags & ~FULL_WIDTH_MASK
    }));
    this.mergeSpans();
  }
  splitSpansAt(index) {
    if (this.spans === void 0 || index <= 0 || index >= this.length)
      return;
    let current = 0;
    for (let i = 0; i < this.spans.length; i++) {
      const span = this.spans[i];
      if (index > current && index < current + span.length) {
        const leftLen = index - current;
        const rightLen = span.length - leftLen;
        this.spans.splice(i, 1, { ...span, length: leftLen }, { ...span, length: rightLen });
        return;
      }
      current += span.length;
    }
  }
  mergeSpans() {
    if (this.spans === void 0)
      return;
    const newSpans = [];
    for (const span of this.spans) {
      if (span.length === 0)
        continue;
      const last = newSpans.at(-1);
      if (last && last.formatFlags === span.formatFlags && last.fgColor === span.fgColor && last.bgColor === span.bgColor && last.link === span.link) {
        last.length += span.length;
      } else {
        newSpans.push({ ...span });
      }
    }
    this.spans = newSpans;
  }
};

// node_modules/ink/build/tokenize.js
var BEL2 = "\x07";
var ESC2 = "\x1B";
var BACKSLASH = "\\";
var CSI = "[";
var OSC2 = "]";
var C1_ST = "\x9C";
var CC_BEL = BEL2.charCodeAt(0);
var CC_ESC = ESC2.charCodeAt(0);
var CC_BACKSLASH = BACKSLASH.charCodeAt(0);
var CC_CSI = CSI.charCodeAt(0);
var CC_OSC = OSC2.charCodeAt(0);
var CC_C1_ST = C1_ST.charCodeAt(0);
var CC_0 = "0".charCodeAt(0);
var CC_9 = "9".charCodeAt(0);
var CC_SEMI = ";".charCodeAt(0);
var CC_M = "m".charCodeAt(0);
var ESCAPES = /* @__PURE__ */ new Set([CC_ESC, 155]);
var linkCodePrefix = `${ESC2}${OSC2}8;`;
var linkCodePrefixCharCodes = [...linkCodePrefix].map((char) => char.charCodeAt(0));
var linkEndCode = `${ESC2}${OSC2}8;;${BEL2}`;
var linkEndCodeST = `${ESC2}${OSC2}8;;${ESC2}${BACKSLASH}`;
var linkEndCodeC1ST = `${ESC2}${OSC2}8;;${C1_ST}`;
var endCodesSet = /* @__PURE__ */ new Set();
var endCodesMap = /* @__PURE__ */ new Map();
for (const [start, end] of ansi_styles_default.codes) {
  endCodesSet.add(ansi_styles_default.color.ansi(end));
  endCodesMap.set(ansi_styles_default.color.ansi(start), ansi_styles_default.color.ansi(end));
}
function getEndCode(code) {
  if (endCodesSet.has(code))
    return code;
  if (endCodesMap.has(code))
    return endCodesMap.get(code);
  if (code.startsWith(linkCodePrefix)) {
    if (code.endsWith("\x1B\\"))
      return linkEndCodeST;
    if (code.endsWith("\x9C"))
      return linkEndCodeC1ST;
    return linkEndCode;
  }
  code = code.slice(2);
  if (code.startsWith("38")) {
    return ansi_styles_default.color.close;
  }
  if (code.startsWith("48")) {
    return ansi_styles_default.bgColor.close;
  }
  const ret = ansi_styles_default.codes.get(Number.parseInt(code, 10));
  if (ret) {
    return ansi_styles_default.color.ansi(ret);
  }
  return ansi_styles_default.reset.open;
}
function findOSCTerminatorIndex(string, startIndex) {
  for (let i = startIndex; i < string.length; i++) {
    const ch = string.charCodeAt(i);
    if (ch === CC_BEL)
      return i;
    if (ch === CC_C1_ST)
      return i;
    if (ch === CC_ESC && i + 1 < string.length && string.charCodeAt(i + 1) === CC_BACKSLASH) {
      return i + 1;
    }
  }
  return -1;
}
function parseLinkCode(string, offset) {
  string = string.slice(offset);
  for (let index = 1; index < linkCodePrefixCharCodes.length; index++) {
    if (string.charCodeAt(index) !== linkCodePrefixCharCodes[index]) {
      return void 0;
    }
  }
  const paramsEndIndex = string.indexOf(";", linkCodePrefix.length);
  if (paramsEndIndex === -1)
    return void 0;
  const endIndex = findOSCTerminatorIndex(string, paramsEndIndex + 1);
  if (endIndex === -1)
    return void 0;
  return string.slice(0, endIndex + 1);
}
function parseOSCSequence(string, offset) {
  string = string.slice(offset);
  const endIndex = findOSCTerminatorIndex(string, 2);
  if (endIndex === -1)
    return void 0;
  return string.slice(0, endIndex + 1);
}
function findSGRSequenceEndIndex(str) {
  for (let index = 2; index < str.length; index++) {
    const charCode = str.charCodeAt(index);
    if (charCode === CC_M)
      return index;
    if (charCode === CC_SEMI)
      continue;
    if (charCode >= CC_0 && charCode <= CC_9)
      continue;
    break;
  }
  return -1;
}
function parseSGRSequence(string, offset) {
  string = string.slice(offset);
  const endIndex = findSGRSequenceEndIndex(string);
  if (endIndex === -1)
    return;
  return string.slice(0, endIndex + 1);
}
function splitCompoundSGRSequences(code) {
  if (!code.includes(";")) {
    return [code];
  }
  const codeParts = code.slice(2, -1).split(";");
  const ret = [];
  for (let i = 0; i < codeParts.length; i++) {
    const rawCode = codeParts[i];
    if (rawCode === "38" || rawCode === "48") {
      if (i + 2 < codeParts.length && codeParts[i + 1] === "5") {
        ret.push(codeParts.slice(i, i + 3).join(";"));
        i += 2;
        continue;
      } else if (i + 4 < codeParts.length && codeParts[i + 1] === "2") {
        ret.push(codeParts.slice(i, i + 5).join(";"));
        i += 4;
        continue;
      }
    }
    ret.push(rawCode);
  }
  return ret.map((part) => `\x1B[${part}m`);
}
function tokenize(str, endChar = Number.POSITIVE_INFINITY) {
  const ret = [];
  let visible = 0;
  let i = 0;
  while (i < str.length) {
    const codePoint = str.codePointAt(i);
    const charLength = codePoint > 65535 ? 2 : 1;
    const charStr = str.slice(i, i + charLength);
    if (ESCAPES.has(codePoint)) {
      let code;
      const nextCodePoint = str.codePointAt(i + 1);
      if (nextCodePoint === CC_OSC) {
        code = parseLinkCode(str, i);
        if (code) {
          ret.push({
            type: "ansi",
            code,
            endCode: getEndCode(code)
          });
        } else {
          code = parseOSCSequence(str, i);
          if (code) {
            ret.push({
              type: "control",
              code
            });
          }
        }
      } else if (nextCodePoint === CC_CSI) {
        code = parseSGRSequence(str, i);
        if (code) {
          const codes = splitCompoundSGRSequences(code);
          for (const individualCode of codes) {
            ret.push({
              type: "ansi",
              code: individualCode,
              endCode: getEndCode(individualCode)
            });
          }
        }
      }
      if (code) {
        i += code.length;
        continue;
      }
    }
    const isVariationSelector = charStr.includes("\uFE0F");
    const isRegionalIndicator = codePoint >= 127462 && codePoint <= 127487;
    const fullWidth = isVariationSelector || isRegionalIndicator || isFullwidthCodePoint(codePoint);
    ret.push({
      type: "char",
      value: charStr,
      fullWidth
    });
    visible += fullWidth ? 2 : 1;
    if (visible >= endChar) {
      break;
    }
    i += charLength;
  }
  return ret;
}
var BOLD_MASK = 1;
var DIM_MASK = 1 << 1;
var ITALIC_MASK = 1 << 2;
var UNDERLINE_MASK = 1 << 3;
var STRIKETHROUGH_MASK = 1 << 4;
var INVERSE_MASK = 1 << 5;
var HIDDEN_MASK = 1 << 6;
var FULL_WIDTH_MASK = 1 << 7;
function styledLineFromTokens(tokens) {
  const line = new StyledLine();
  let formatFlags = 0;
  let fgColor;
  let bgColor;
  let link2;
  for (const token of tokens) {
    if (token.type === "ansi") {
      const { code } = token;
      switch (code) {
        case ansi_styles_default.reset.open: {
          formatFlags = 0;
          fgColor = void 0;
          bgColor = void 0;
          link2 = void 0;
          break;
        }
        case ansi_styles_default.bold.open: {
          formatFlags |= BOLD_MASK;
          break;
        }
        case ansi_styles_default.dim.open: {
          formatFlags |= DIM_MASK;
          break;
        }
        case ansi_styles_default.italic.open: {
          formatFlags |= ITALIC_MASK;
          break;
        }
        case ansi_styles_default.underline.open: {
          formatFlags |= UNDERLINE_MASK;
          break;
        }
        case ansi_styles_default.strikethrough.open: {
          formatFlags |= STRIKETHROUGH_MASK;
          break;
        }
        case ansi_styles_default.inverse.open: {
          formatFlags |= INVERSE_MASK;
          break;
        }
        case ansi_styles_default.hidden.open: {
          formatFlags |= HIDDEN_MASK;
          break;
        }
        case ansi_styles_default.bold.close:
        case ansi_styles_default.dim.close: {
          formatFlags &= ~BOLD_MASK;
          formatFlags &= ~DIM_MASK;
          break;
        }
        case ansi_styles_default.italic.close: {
          formatFlags &= ~ITALIC_MASK;
          break;
        }
        case ansi_styles_default.underline.close: {
          formatFlags &= ~UNDERLINE_MASK;
          break;
        }
        case ansi_styles_default.strikethrough.close: {
          formatFlags &= ~STRIKETHROUGH_MASK;
          break;
        }
        case ansi_styles_default.inverse.close: {
          formatFlags &= ~INVERSE_MASK;
          break;
        }
        case ansi_styles_default.hidden.close: {
          formatFlags &= ~HIDDEN_MASK;
          break;
        }
        default: {
          if (code.startsWith("\x1B[38;") || code >= "\x1B[30m" && code <= "\x1B[37m" || code >= "\x1B[90m" && code <= "\x1B[97m") {
            fgColor = code;
          } else if (code.startsWith("\x1B[48;") || code >= "\x1B[40m" && code <= "\x1B[47m" || code >= "\x1B[100m" && code <= "\x1B[107m") {
            bgColor = code;
          } else if (code === ansi_styles_default.color.close) {
            fgColor = void 0;
          } else if (code === ansi_styles_default.bgColor.close) {
            bgColor = void 0;
          } else if (code.startsWith(linkCodePrefix)) {
            link2 = code;
          } else if (code === linkEndCode || code === linkEndCodeST || code === linkEndCodeC1ST) {
            link2 = void 0;
          }
        }
      }
    } else if (token.type === "char") {
      let finalFlags = formatFlags;
      if (token.fullWidth) {
        finalFlags |= FULL_WIDTH_MASK;
      }
      line.pushChar(token.value, finalFlags, fgColor, bgColor, link2);
    }
  }
  return line;
}
function styledLineToString(line) {
  let ret = "";
  let prevFormatFlags = 0;
  let prevFgColor;
  let prevBgColor;
  let prevLink;
  for (const { value, formatFlags, fgColor, bgColor, link: link2 } of line) {
    if (formatFlags === prevFormatFlags && fgColor === prevFgColor && bgColor === prevBgColor && link2 === prevLink) {
      ret += value;
      continue;
    }
    let needResetBoldDim = false;
    if (prevFormatFlags & BOLD_MASK && !(formatFlags & BOLD_MASK) || prevFormatFlags & DIM_MASK && !(formatFlags & DIM_MASK)) {
      needResetBoldDim = true;
    }
    if (needResetBoldDim) {
      ret += ansi_styles_default.bold.close;
    }
    if ((needResetBoldDim || formatFlags & BOLD_MASK && !(prevFormatFlags & BOLD_MASK)) && formatFlags & BOLD_MASK)
      ret += ansi_styles_default.bold.open;
    if ((needResetBoldDim || formatFlags & DIM_MASK && !(prevFormatFlags & DIM_MASK)) && formatFlags & DIM_MASK)
      ret += ansi_styles_default.dim.open;
    if (formatFlags & ITALIC_MASK && !(prevFormatFlags & ITALIC_MASK))
      ret += ansi_styles_default.italic.open;
    if (!(formatFlags & ITALIC_MASK) && prevFormatFlags & ITALIC_MASK)
      ret += ansi_styles_default.italic.close;
    if (formatFlags & UNDERLINE_MASK && !(prevFormatFlags & UNDERLINE_MASK))
      ret += ansi_styles_default.underline.open;
    if (!(formatFlags & UNDERLINE_MASK) && prevFormatFlags & UNDERLINE_MASK)
      ret += ansi_styles_default.underline.close;
    if (formatFlags & STRIKETHROUGH_MASK && !(prevFormatFlags & STRIKETHROUGH_MASK))
      ret += ansi_styles_default.strikethrough.open;
    if (!(formatFlags & STRIKETHROUGH_MASK) && prevFormatFlags & STRIKETHROUGH_MASK)
      ret += ansi_styles_default.strikethrough.close;
    if (formatFlags & INVERSE_MASK && !(prevFormatFlags & INVERSE_MASK))
      ret += ansi_styles_default.inverse.open;
    if (!(formatFlags & INVERSE_MASK) && prevFormatFlags & INVERSE_MASK)
      ret += ansi_styles_default.inverse.close;
    if (formatFlags & HIDDEN_MASK && !(prevFormatFlags & HIDDEN_MASK))
      ret += ansi_styles_default.hidden.open;
    if (!(formatFlags & HIDDEN_MASK) && prevFormatFlags & HIDDEN_MASK)
      ret += ansi_styles_default.hidden.close;
    if (fgColor !== prevFgColor) {
      ret += fgColor === void 0 ? ansi_styles_default.color.close : fgColor;
    }
    if (bgColor !== prevBgColor) {
      ret += bgColor === void 0 ? ansi_styles_default.bgColor.close : bgColor;
    }
    if (link2 !== prevLink) {
      ret += link2 === void 0 ? linkEndCode : link2;
    }
    ret += value;
    prevFormatFlags = formatFlags;
    prevFgColor = fgColor;
    prevBgColor = bgColor;
    prevLink = link2;
  }
  if (prevFgColor !== void 0)
    ret += ansi_styles_default.color.close;
  if (prevBgColor !== void 0)
    ret += ansi_styles_default.bgColor.close;
  if (prevFormatFlags & (BOLD_MASK | DIM_MASK))
    ret += ansi_styles_default.bold.close;
  if (prevFormatFlags & ITALIC_MASK)
    ret += ansi_styles_default.italic.close;
  if (prevFormatFlags & UNDERLINE_MASK)
    ret += ansi_styles_default.underline.close;
  if (prevFormatFlags & STRIKETHROUGH_MASK)
    ret += ansi_styles_default.strikethrough.close;
  if (prevFormatFlags & INVERSE_MASK)
    ret += ansi_styles_default.inverse.close;
  if (prevFormatFlags & HIDDEN_MASK)
    ret += ansi_styles_default.hidden.close;
  if (prevLink !== void 0)
    ret += linkEndCode;
  return ret;
}

// node_modules/mnemonist/index.mjs
var import_fibonacci_heap = __toESM(require_fibonacci_heap(), 1);
var import_heap = __toESM(require_heap(), 1);
var import_suffix_array = __toESM(require_suffix_array(), 1);
var import_vector = __toESM(require_vector(), 1);
var import_lru_map_with_delete = __toESM(require_lru_map_with_delete(), 1);
var MinFibonacciHeap = import_fibonacci_heap.default.MinFibonacciHeap;
var MaxFibonacciHeap = import_fibonacci_heap.default.MaxFibonacciHeap;
var MinHeap = import_heap.default.MinHeap;
var MaxHeap = import_heap.default.MaxHeap;
var GeneralizedSuffixArray = import_suffix_array.default.GeneralizedSuffixArray;
var Uint8Vector = import_vector.default.Uint8Vector;
var Uint8ClampedVector = import_vector.default.Uint8ClampedVector;
var Int8Vector = import_vector.default.Int8Vector;
var Uint16Vector = import_vector.default.Uint16Vector;
var Int16Vector = import_vector.default.Int16Vector;
var Uint32Vector = import_vector.default.Uint32Vector;
var Int32Vector = import_vector.default.Int32Vector;
var Float32Vector = import_vector.default.Float32Vector;
var Float64Vector = import_vector.default.Float64Vector;
var PointerVector = import_vector.default.PointerVector;

// node_modules/ink/build/data-limited-lru-map.js
var DataLimitedLruMap = class {
  map;
  maxDataSize;
  currentDataSize = 0;
  constructor(maxKeys, maxDataSize) {
    this.map = new import_lru_map_with_delete.default(maxKeys);
    this.maxDataSize = maxDataSize;
  }
  get(key) {
    return this.map.get(key);
  }
  set(key, value) {
    const size = key.length;
    const hasKey = this.map.has(key);
    while (this.currentDataSize + size > this.maxDataSize && this.map.size > 0) {
      const map = this.map;
      const lruKey = map.K[map.tail];
      if (lruKey === void 0) {
        break;
      }
      if (!this.map.delete(lruKey)) {
        break;
      }
      this.currentDataSize -= lruKey.length;
    }
    const result = this.map.setpop(key, value);
    if (result?.evicted) {
      this.currentDataSize -= result.key.length;
    }
    if (hasKey) {
      this.currentDataSize -= size;
    }
    this.currentDataSize += size;
  }
  get size() {
    return this.map.size;
  }
  get currentDataSizeValue() {
    return this.currentDataSize;
  }
  clear() {
    this.map.clear();
    this.currentDataSize = 0;
  }
};

// node_modules/ink/build/measure-text.js
var toStyledCharactersCache = new DataLimitedLruMap(2e3, 1e5);
var toStyledCharactersCacheEnabled = true;
function toStyledCharacters(text) {
  if (toStyledCharactersCacheEnabled) {
    const cached = toStyledCharactersCache.get(text);
    if (cached !== void 0) {
      return cached;
    }
  }
  const tokens = tokenize(text);
  const characters = styledLineFromTokens(tokens);
  const combinedLine = new StyledLine();
  for (let i = 0; i < characters.length; i++) {
    const value = characters.getValue(i);
    const formatFlags = characters.getFormatFlags(i);
    const fgColor = characters.getFgColor(i);
    const bgColor = characters.getBgColor(i);
    const link2 = characters.getLink(i);
    if (value === "	") {
      for (let j = 0; j < 4; j++) {
        combinedLine.pushChar(" ", formatFlags, fgColor, bgColor, link2);
      }
      continue;
    }
    if (value === "\b") {
      continue;
    }
    let combinedValue = value;
    let isCombined = false;
    const firstCodePoint = combinedValue.codePointAt(0);
    if (firstCodePoint && firstCodePoint >= 127462 && firstCodePoint <= 127487 && i + 1 < characters.length) {
      const nextValue = characters.getValue(i + 1);
      const nextFirstCodePoint = nextValue.codePointAt(0);
      if (nextFirstCodePoint && nextFirstCodePoint >= 127462 && nextFirstCodePoint <= 127487) {
        combinedValue += nextValue;
        i++;
        isCombined = true;
      }
    }
    if (!isCombined) {
      while (i + 1 < characters.length) {
        const nextValue = characters.getValue(i + 1);
        if (!nextValue)
          break;
        const nextFirstCodePoint = nextValue.codePointAt(0);
        if (!nextFirstCodePoint)
          break;
        const isUnicodeMark = /\p{Mark}/u.test(nextValue);
        const isSkinToneModifier = nextFirstCodePoint >= 127995 && nextFirstCodePoint <= 127999;
        const isZeroWidthJoiner = nextFirstCodePoint === 8205;
        const isTagsBlock = nextFirstCodePoint >= 917504 && nextFirstCodePoint <= 917631;
        const isCombining = isUnicodeMark || isSkinToneModifier || isZeroWidthJoiner || isTagsBlock || nextFirstCodePoint === 3635 || // Thai SARA AM
        nextFirstCodePoint === 3763;
        if (!isCombining) {
          break;
        }
        combinedValue += nextValue;
        i++;
        if (isZeroWidthJoiner && i + 1 < characters.length) {
          const characterAfterZwj = characters.getValue(i + 1);
          if (characterAfterZwj) {
            combinedValue += characterAfterZwj;
            i++;
          }
        }
      }
    }
    combinedLine.pushChar(combinedValue, formatFlags, fgColor, bgColor, link2);
  }
  if (toStyledCharactersCacheEnabled) {
    toStyledCharactersCache.set(text, combinedLine);
  }
  return combinedLine;
}

// node_modules/yoga-layout/dist/binaries/yoga-wasm-base64-esm.js
var loadYoga = (() => {
  var _scriptDir = import.meta.url;
  return function(loadYoga2) {
    loadYoga2 = loadYoga2 || {};
    var h;
    h || (h = typeof loadYoga2 !== "undefined" ? loadYoga2 : {});
    var aa, ca;
    h.ready = new Promise(function(a, b) {
      aa = a;
      ca = b;
    });
    var da = Object.assign({}, h), q = "";
    "undefined" != typeof document && document.currentScript && (q = document.currentScript.src);
    _scriptDir && (q = _scriptDir);
    0 !== q.indexOf("blob:") ? q = q.substr(0, q.replace(/[?#].*/, "").lastIndexOf("/") + 1) : q = "";
    var ea = h.print || console.log.bind(console), v = h.printErr || console.warn.bind(console);
    Object.assign(h, da);
    da = null;
    var w;
    h.wasmBinary && (w = h.wasmBinary);
    var noExitRuntime = h.noExitRuntime || true;
    "object" != typeof WebAssembly && x("no native wasm support detected");
    var fa, ha = false;
    function z(a, b, c) {
      c = b + c;
      for (var d = ""; !(b >= c); ) {
        var e = a[b++];
        if (!e) break;
        if (e & 128) {
          var f = a[b++] & 63;
          if (192 == (e & 224)) d += String.fromCharCode((e & 31) << 6 | f);
          else {
            var g = a[b++] & 63;
            e = 224 == (e & 240) ? (e & 15) << 12 | f << 6 | g : (e & 7) << 18 | f << 12 | g << 6 | a[b++] & 63;
            65536 > e ? d += String.fromCharCode(e) : (e -= 65536, d += String.fromCharCode(55296 | e >> 10, 56320 | e & 1023));
          }
        } else d += String.fromCharCode(e);
      }
      return d;
    }
    var ia, ja, A, C, ka, D, E, la, ma;
    function na() {
      var a = fa.buffer;
      ia = a;
      h.HEAP8 = ja = new Int8Array(a);
      h.HEAP16 = C = new Int16Array(a);
      h.HEAP32 = D = new Int32Array(a);
      h.HEAPU8 = A = new Uint8Array(a);
      h.HEAPU16 = ka = new Uint16Array(a);
      h.HEAPU32 = E = new Uint32Array(a);
      h.HEAPF32 = la = new Float32Array(a);
      h.HEAPF64 = ma = new Float64Array(a);
    }
    var oa, pa = [], qa = [], ra = [];
    function sa() {
      var a = h.preRun.shift();
      pa.unshift(a);
    }
    var F = 0, ta = null, G = null;
    function x(a) {
      if (h.onAbort) h.onAbort(a);
      a = "Aborted(" + a + ")";
      v(a);
      ha = true;
      a = new WebAssembly.RuntimeError(a + ". Build with -sASSERTIONS for more info.");
      ca(a);
      throw a;
    }
    function ua(a) {
      return a.startsWith("data:application/octet-stream;base64,");
    }
    var H;
    H = "data:application/octet-stream;base64,AGFzbQEAAAABugM3YAF/AGACf38AYAF/AX9gA39/fwBgAn98AGACf38Bf2ADf39/AX9gBH9/f30BfWADf398AGAAAGAEf39/fwBgAX8BfGACf38BfGAFf39/f38Bf2AAAX9gA39/fwF9YAZ/f31/fX8AYAV/f39/fwBgAn9/AX1gBX9/f319AX1gAX8BfWADf35/AX5gB39/f39/f38AYAZ/f39/f38AYAR/f39/AX9gBn9/f319fQF9YAR/f31/AGADf399AX1gBn98f39/fwF/YAR/fHx/AGACf30AYAh/f39/f39/fwBgDX9/f39/f39/f39/f38AYAp/f39/f39/f39/AGAFf39/f38BfGAEfHx/fwF9YA1/fX1/f399fX9/f39/AX9gB39/f319f38AYAJ+fwF/YAN/fX0BfWABfAF8YAN/fHwAYAR/f319AGAHf39/fX19fQF9YA1/fX99f31/fX19fX1/AX9gC39/f39/f399fX19AX9gCH9/f39/f319AGAEf39+fgBgB39/f39/f38Bf2ACfH8BfGAFf398fH8AYAN/f38BfGAEf39/fABgA39/fQBgBn9/fX99fwF/ArUBHgFhAWEAHwFhAWIAAwFhAWMACQFhAWQAFgFhAWUAEQFhAWYAIAFhAWcAAAFhAWgAIQFhAWkAAwFhAWoAAAFhAWsAFwFhAWwACgFhAW0ABQFhAW4AAwFhAW8AAQFhAXAAFwFhAXEABgFhAXIAAAFhAXMAIgFhAXQACgFhAXUADQFhAXYAFgFhAXcAAgFhAXgAAwFhAXkAGAFhAXoAAgFhAUEAAQFhAUIAEQFhAUMAAQFhAUQAAAOiAqACAgMSBwcACRkDAAoRBgYKEwAPDxMBBiMTCgcHGgMUASQFJRQHAwMKCgMmAQYYDxobFAAKBw8KBwMDAgkCAAAFGwACBwIHBgIDAQMIDAABKAkHBQURACkZASoAAAIrLAIALQcHBy4HLwkFCgMCMA0xAgMJAgACAQYKAQIBBQEACQIFAQEABQAODQ0GFQIBHBUGAgkCEAAAAAUyDzMMBQYINAUCAwUODg41AgMCAgIDBgICNgIBDAwMAQsLCwsLCx0CAAIAAAABABABBQICAQMCEgMMCwEBAQEBAQsLAQICAwICAgICAgIDAgIICAEICAgEBAQEBAQEBAQABAQABAQEBAAE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GiABQQA2AvADIAFCADcC6AMgAigC7AMiAyACKALoAyIERwRAIAMgBGsiBEEASA0FIAEgBBAeIgM2AuwDIAEgAzYC6AMgASADIARqNgLwAyACKALoAyIEIAIoAuwDIghHBEADQCADIAQoAgA2AgAgA0EEaiEDIARBBGoiBCAIRw0ACwsgASADNgLsAwsgASACKQL0AzcC9AMgASACKAKEBDYChAQgASACKQL8AzcC/AMgAUEANgLkAwsgBSABNgIAIAEgADYC5AMLIAZBAWohBiAFQQRqIgUgB0cNAAsLDwsQAgALUAACQAJAAkACQAJAIAIOBAQAAQIDCyAAIAEgAUEwahBDDwsgACABIAFBMGogAxBEDwsgACABIAFBMGoQQg8LECQACyAAIAEgAUEwaiADEEULcAIBfwF9IwBBEGsiBCQAIARBCGogACABQQJ0QdwlaigCACACEDZDAADAfyEFAkACQAJAIAQtAAxBAWsOAgABAgsgBCoCCCEFDAELIAQqAgggA5RDCtcjPJQhBQsgBEEQaiQAIAVDAAAAACAFIAVbGwt5AgF/AX0jAEEQayIDJAAgA0EIaiAAIAFBAnRB7CVqKAIAIAIQU0MAAMB/IQQCQAJAAkAgAy0ADEEBaw4CAAECCyADKgIIIQQMAQsgAyoCCEMAAAAAlEMK1yM8lCEECyADQRBqJAAgBEMAAAAAl0MAAAAAIAQgBFsbC1QAAkACQAJAAkACQCACDgQEAAECAwsgACABIAFBwgBqEEMPCyAAIAEgAUHCAGogAxBEDwsgACABIAFBwgBqEEIPCxAkAAsgACABIAFBwgBqIAMQRQsvACAAIAJFQQF0IgIgASADEGAgACACIAEQS5IgACACIAEgAxB/IAAgAiABEFKSkgvOAQIDfwJ9IwBBEGsiAyQAQQEhBCADQQhqIABB/ABqIgUgACABQQF0akH2AGoiAS8BABAfAkACQCADKgIIIgcgAioCACIGXARAIAcgB1sEQCACLQAEIQIMAgsgBiAGXCEECyACLQAEIQIgBEUNACADLQAMIAJB/wFxRg0BCyAFIAEgBiACEDkDQCAALQAAIgFBBHENASAAIAFBBHI6AAAgACgCECIBBEAgACABEQAACyAAQYCAgP4HNgKcASAAKALkAyIADQALCyADQRBqJAALzgECA38CfSMAQRBrIgMk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AWsOAgABAgsgBCoCCCEFDAELIAQqAgggA5RDCtcjPJQhBQsgBEEQaiQAIAVDAAAAACAFIAVbGwscACAAIAFBCCACpyACQiCIpyADpyADQiCIpxAVCwUAEFgACzkAIABFBEBBAA8LAn8gAUGAf3FBgL8DRiABQf8ATXJFBEBB/DtBGTYCAEF/DAELIAAgAToAAEEBCwvEAgACQAJAAkACQAJAAkACQAJAAkACQAJAAkACQCABQQlrDhIACgsMCgsCAwQFDAsMDAoLBwgJCyACIAIoAgAiAUEEajYCACAAIAEoAgA2AgAPCwALIAIgAigCACIBQQRqNgIAIAAgATIBADcDAA8LIAIgAigCACIBQQRqNgIAIAAgATMBADcDAA8LIAIgAigCACIBQQRqNgIAIAAgATAAADcDAA8LIAIgAigCACIBQQRqNgIAIAAgATEAADcDAA8LAAsgAiACKAIAQQdqQXhxIgFBCGo2AgAgACABKwMAOQMADwsgACACIAMRAQALDwsgAiACKAIAIgFBBGo2AgAgACABNAIANwMADwsgAiACKAIAIgFBBGo2AgAgACABNQIANwMADwsgAiACKAIAQQdqQXhxIgFBCGo2AgAgACABKQMANwMAC84BAgN/An0jAEEQayIDJABBASEEIANBCGogAEH8AGoiBSAAIAFBAXRqQegAaiIBLwEAEB8CQAJAIAMqAggiByACKgIAIgZcBEAgByAHWwRAIAItAAQhAgwCCyAGIAZcIQQLIAItAAQhAiAERQ0AIAMtAAwgAkH/AXFGDQELIAUgASAGIAIQOQNAIAAtAAAiAUEEcQ0BIAAgAUEEcjoAACAAKAIQIgEEQCAAIAERAAALIABBgICA/gc2ApwBIAAoAuQDIgANAAsLIANBEGokAAtdAQR/IAAoAgAhAgNAIAIsAAAiAxBXBEBBfyEEIAAgAkEBaiICNgIAIAFBzJmz5gBNBH9BfyADQTBrIgMgAUEKbCIEaiADIARB/////wdzShsFIAQLIQEMAQsLIAELrhQCEn8BfiMAQdAAayIIJAAgCCABNgJMIAhBN2ohFyAIQThqIRQCQAJAAkACQANAIAEhDSAHIA5B/////wdzSg0BIAcgDmohDgJAAkACQCANIgctAAAiCQRAA0ACQAJAIAlB/wFxIgFFBEAgByEBDAELIAFBJUcNASAH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IQEgAEIANwIEIAAgATYCACABIAA2AgQgAkEQaiQAIAALGwEBfyAABEAgACgCACIBBEAgARAjCyAAECMLC0kBAn9BBBAeIQFBIBAeIgBBADYCHCAAQoCAgICAgIDAPzcCFCAAQgA3AgwgAEEAOgAIIABBAzYCBCAAQQA2AgAgASAANgIAIAELIAAgAkEFR0EAIAIbRQRAQbgwIAMgBBBJDwsgAyAEEHALIgEBfiABIAKtIAOtQiCGhCAEIAARFQAiBUIgiKckASAFpwuoAQEFfyAAKAJUIgMoAgAhBSADKAIEIgQgACgCFCAAKAIcIgdrIgYgBCAGSRsiBgRAIAUgByAGECsaIAMgAygCACAGaiIFNgIAIAMgAygCBCAGayIENgIECyAEIAIgAiAESxsiBARAIAUgASAEECsaIAMgAygCACAEaiIFNgIAIAMgAygCBCAEazYCBAsgBUEAOgAAIAAgACgCLCIBNgIcIAAgATYCFCACCwQAQgALBABBAAuKBQIGfgJ/IAEgASgCAEEHakF4cSIBQRBqNgIAIAAhCSABKQMAIQMgASkDCCEGIwBBIGsiCCQAAkAgBkL///////////8AgyIEQoCAgICAgMCAPH0gBEKAgICAgIDA/8MAfVQEQCAGQgSGIANCPIiEIQQgA0L//////////w+DIgNCgYCAgICAgIAIWgRAIARCgYCAgICAgIDAAHwhAgwCCyAEQoCAgICAgICAQH0hAiADQoCAgICAgICACFINASACIARCAYN8IQIMAQsgA1AgBEKAgICAgIDA//8AVCAEQoCAgICAgMD//wBRG0UEQCAGQgSGIANCPIiEQv////////8Dg0KAgICAgICA/P8AhCECDAELQoCAgICAgID4/wAhAiAEQv///////7//wwBWDQBCACECIARCMIinIgBBkfcASQ0AIAMhAiAGQv///////z+DQoCAgICAgMAAhCIFIQcCQCAAQYH3AGsiAUHAAHEEQCACIAFBQGqthiEHQgAhAgwBCyABRQ0AIAcgAa0iBIYgAkHAACABa62IhCEHIAIgBIYhAgsgCCACNwMQIAggBzcDGAJAQYH4ACAAayIAQcAAcQRAIAUgAEFAaq2IIQNCACEFDAELIABFDQAgBUHAACAAa62GIAMgAK0iAoiEIQMgBSACiCEFCyAIIAM3AwAgCCAF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ASAAKAIAIQAgASACQQFxBH8gASgCACAAaigCAAUgAAsRCwALYQECfyMAQRBrIgIkACABIAAoAgQiA0EBdWohASAAKAIAIQAgAiABIANBAXEEfyABKAIAIABqKAIABSAACxEBAEEQEB4iACACKQMINwMIIAAgAikDADcDACACQRBqJAAgAAtjAQJ/IwBBEGsiAyQAIAEgACgCBCIEQQF1aiEBIAAoAgAhACADIAEgAiAEQQFxBH8gASgCACAAaigCAAUgAAsRAwBBEBAeIgAgAykDCDcDCCAAIAMpAwA3AwAgA0EQaiQAIAALNwEBfyABIAAoAgQiA0EBdWohASAAKAIAIQAgASACIANBAXEEfyABKAIAIABqKAIABSAACxEEAAs5AQF/IAEgACgCBCIEQQF1aiEBIAAoAgAhACABIAIgAyAEQQFxBH8gASgCACAAaigCAAUgAAsRCAALCQAgASAAEQIACwUAQcM7Cw8AIAEgACgCAGogAjYCAAsNACABIAAoAgBqKAIACxgBAX9BEBAeIgBCADcDCCAAQQA2AgAgAAsYAQF/QRAQHiIAQgA3AwAgAEIANwMIIAALDABBMBAeQQBBMBAqCzcBAX8gASAAKAIEIgNBAXVqIQEgACgCACEAIAEgAiADQQFxBH8gASgCACAAaigCAAUgAAsRHgALBQBBvjsLIQAgACABKAIAIAEgASwAC0EASBtBuzsgAigCABAQNgIACyoBAX9BDBAeIgFBADoABCABIAAoAgA2AgggAEEANgIAIAFB2Cc2AgAgAQsFAEG7OwsFAEG4OwshACAAIAEoAgAgASABLAALQQBIG0GkOyACKAIAEBA2AgAL2AEBBH8jAEEgayIDJAAgASgCACIEQfD///8HSQRAAkACQCAEQQtPBEAgBEEPckEBaiIFEB4hBiADIAVBgICAgHhyNgIQIAMgBjYCCCADIAQ2AgwgBCAGaiEFDAELIAMgBDoAEyADQQhqIgYgBGohBSAERQ0BCyAGIAFBBGogBBArGgsgBUEAOgAAIAMgAjYCACADQRhqIANBCGogAyAAEQMAIAMoAhgQHSADKAIYIgAQBiADKAIAEAYgAywAE0EASARAIAMoAggQIwsgA0EgaiQAIAAPCxACAAsqAQF/QQwQHiIBQQA6AAQgASAAKAIANgIIIABBADYCACABQeAmNgIA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AkEIaiAIIAYQHyACIAcgAC8AABAfQQEhAyACKgIIIgogAioCACILXAR/IAogClsNAyALIAtcBSADC0UNAiACLQAMIAItAARHDQILIABBAmohAEEBIQMgBCEGQQEhBCAGRQ0ACyABLwB6IgBBB3FFBEAgBS0AekEHcUUNAgsgCCAAECAiCiAHIAUvAHoQICILWw0BIAogClsNACALIAtcDQELIAFBFGogBUEUakHoABArGiABQfwAaiAFQfwAahCgAQNAIAEtAAAiAEEEcQ0BIAEgAEEEcjoAACABKAIQIgAEQCABIAARAAALIAFBgICA/gc2ApwBIAEoAuQDIgENAAsLIAJBEGokAAvGAwEEfyMAQaAEayICJAAgACgCBCEBIABBADYCBCABBEAgASABKAIAKAIEEQAACyAAKAIIIQEgAEEANgIIIAEEQCABIAEoAgAoAgQRAAALAkAgACgCACIAKALoAyAAKALsA0YEQCAAKALkAw0BIAAgAkEYaiAAKAL0AxBcIgEpAgA3AgAgACABKAIQNgIQIAAgASkCCDcCCCAAQRRqIAFBFGpB6AAQKxogACABKQKMATcCjAEgACABKQKEATcChAEgACABKQJ8NwJ8IAEoApQBIQQgAUEANgKUASAAKAKUASEDIAAgBDYClAEgAwRAIAMQWwsgAEGYAWogAUGYAWpB0AIQKxogACgC6AMiAwRAIAAgAzYC7AMgAxAjCyAAIAEoAugDNgLoAyAAIAEoAuwDNgLsAyAAIAEoAvADNgLwAyABQQA2AvADIAFCADcC6AMgACABKQL8AzcC/AMgACABKQL0AzcC9AMgACABKAKEBDYChAQgASgClAEhACABQQA2ApQBIAAEQCAAEFsLIAJBoARqJAAPCyACQfAcNgIQIABBBUHYJSACQRBqECwQJAALIAJB5hE2AgAgAEEFQdglIAIQLBAkAAsLAEEMEB4gABCiAQsLAEEMEB5BABCiAQsNACAAKAIALQAIQQFxCwoAIAAoAgAoAhQLGQAgAUH/AXEEQBACAAsgACgCACgCEEEBcQsYACAAKAIAIgAgAC0ACEH+AXEgAXI6AAgLJgAgASAAKAIAIgAoAhRHBEAgACABNgIUIAAgACgCDEEBajYCDAsLkgEBAn8jAEEQayICJAAgACgCACEAIAFDAAAAAGAEQCABIAAqAhhcBEAgACABOAIYIAAgACgCDEEBajYCDAsgAkEQaiQADwsgAkGIFDYCACMAQRBrIgMkACADIAI2AgwCQCAARQRAQbgwQdglIAIQSRoMAQsgAEEAQQVB2CUgAiAAKAIEEQ0AGgsgA0EQaiQAECQACz8AIAFB/wFxRQRAIAIgACgCACIAKAIQIgFBAXFHBEAgACABQX5xIAJyNgIQIAAgACgCDEEBajYCDAsPCxACAAsL4CYjAEGACAuBHk9ubHkgbGVhZiBub2RlcyB3aXRoIGN1c3RvbSBtZWFzdXJlIGZ1bmN0aW9ucyBzaG91bGQgbWFudWFsbHkgbWFyayB0aGVtc2VsdmVzIGFzIGRpcnR5AGlzRGlydHkAbWFya0RpcnR5AGRlc3Ryb3kAc2V0RGlzcGxheQBnZXREaXNwbGF5AHNldEZsZXgALSsgICAwWDB4AC0wWCswWCAwWC0weCsweCAweABzZXRGbGV4R3JvdwBnZXRGbGV4R3JvdwBzZXRPdmVyZmxvdwBnZXRPdmVyZmxvdwBoYXNOZXdMYXlvdXQAY2FsY3VsYXRlTGF5b3V0AGdldENvbXB1dGVkTGF5b3V0AHVuc2lnbmVkIHNob3J0AGdldENoaWxkQ291bnQAdW5zaWduZWQgaW50AHNldEp1c3RpZnlDb250ZW50AGdldEp1c3RpZnlDb250ZW50AGF2YWlsYWJsZUhlaWdodCBpcyBpbmRlZmluaXRlIHNvIGhlaWdodFNpemluZ01vZGUgbXVzdCBiZSBTaXppbmdNb2RlOjpNYXhDb250ZW50AGF2YWlsYWJsZVdpZHRoIGlzIGluZGVmaW5pdGUgc28gd2lkdGhTaXppbmdNb2RlIG11c3QgYmUgU2l6aW5nTW9kZTo6TWF4Q29udGVudABzZXRBbGlnbkNvbnRlbnQAZ2V0QWxpZ25Db250ZW50AGdldFBhcmVudABpbXBsZW1lbnQAc2V0TWF4SGVpZ2h0UGVyY2VudABzZXRIZWlnaHRQZXJjZW50AHNldE1pbkhlaWdodFBlcmNlbnQAc2V0RmxleEJhc2lzUGVyY2VudABzZXRHYXBQZXJjZW50AHNldFBvc2l0aW9uUGVyY2VudABzZXRNYXJnaW5QZXJjZW50AHNldE1heFdpZHRoUGVyY2VudABzZXRXaWR0aFBlcmNlbnQAc2V0TWluV2lkdGhQZXJjZW50AHNldFBhZGRpbmdQZXJjZW50AGhhbmRsZS50eXBlKCkgPT0gU3R5bGVWYWx1ZUhhbmRsZTo6VHlwZTo6UG9pbnQgfHwgaGFuZGxlLnR5cGUoKSA9PSBTdHlsZVZhbHVlSGFuZGxlOjpUeXBlOjpQZXJjZW50AGNyZWF0ZURlZmF1bHQAdW5pdAByaWdodABoZWlnaHQAc2V0TWF4SGVpZ2h0AGdldE1heEhlaWdodABzZXRIZWlnaHQAZ2V0SGVpZ2h0AHNldE1pbkhlaWdodABnZXRNaW5IZWlnaHQAZ2V0Q29tcHV0ZWRIZWlnaHQAZ2V0Q29tcHV0ZWRSaWdodABsZWZ0AGdldENvbXB1dGVkTGVmdAByZXNldABfX2Rlc3RydWN0AGZsb2F0AHVpbnQ2NF90AHVzZVdlYkRlZmF1bHRzAHNldFVzZVdlYkRlZmF1bHRzAHNldEFsaWduSXRlbXMAZ2V0QWxpZ25JdGVtcwBzZXRGbGV4QmFzaXMAZ2V0RmxleEJhc2lzAENhbm5vdCBnZXQgbGF5b3V0IHByb3BlcnRpZXMgb2YgbXVsdGktZWRnZSBzaG9ydGhhbmRzAHNldFBvaW50U2NhbGVGYWN0b3IATWVhc3VyZUNhbGxiYWNrV3JhcHBlcgBEaXJ0aWVkQ2FsbGJhY2tXcmFwcGVyAENhbm5vdCByZXNldCBhIG5vZGUgc3RpbGwgYXR0YWNoZWQgdG8gYSBvd25lcgBzZXRCb3JkZXIAZ2V0Qm9yZGVyAGdldENvbXB1dGVkQm9yZGVyAGdldE51bWJlcgBoYW5kbGUudHlwZSgpID09IFN0eWxlVmFsdWVIYW5kbGU6OlR5cGU6Ok51bWJlcgB1bnNpZ25lZCBjaGFyAHRvcABnZXRDb21wdXRlZFRvcABzZXRGbGV4V3JhcABnZXRGbGV4V3JhcABzZXRHYXAAZ2V0R2FwACVwAHNldEhlaWdodEF1dG8Ac2V0RmxleEJhc2lzQXV0bwBzZXRQb3NpdGlvbkF1dG8Ac2V0TWFyZ2luQXV0bwBzZXRXaWR0aEF1dG8AU2NhbGUgZmFjdG9yIHNob3VsZCBub3QgYmUgbGVzcyB0aGFuIHplcm8Ac2V0QXNwZWN0UmF0aW8AZ2V0QXNwZWN0UmF0aW8Ac2V0UG9zaXRpb24AZ2V0UG9zaXRpb24Abm90aWZ5T25EZXN0cnVjdGlvbgBzZXRGbGV4RGlyZWN0aW9uAGdldEZsZXhEaXJlY3Rpb24Ac2V0RGlyZWN0aW9uAGdldERpcmVjdGlvbgBzZXRNYXJnaW4AZ2V0TWFyZ2luAGdldENvbXB1dGVkTWFyZ2luAG1hcmtMYXlvdXRTZWVuAG5hbgBib3R0b20AZ2V0Q29tcHV0ZWRCb3R0b20AYm9vbABlbXNjcmlwdGVuOjp2YWwAc2V0RmxleFNocmluawBnZXRGbGV4U2hyaW5rAHNldEFsd2F5c0Zvcm1zQ29udGFpbmluZ0Jsb2NrAE1lYXN1cmVDYWxsYmFjawBEaXJ0aWVkQ2FsbGJhY2sAZ2V0TGVuZ3RoAHdpZHRoAHNldE1heFdpZHRoAGdldE1heFdpZHRoAHNldFdpZHRoAGdldFdpZHRoAHNldE1pbldpZHRoAGdldE1pbldpZHRoAGdldENvbXB1dGVkV2lkdGgAcHVzaAAvaG9tZS9ydW5uZXIvd29yay95b2dhL3lvZ2EvamF2YXNjcmlwdC8uLi95b2dhL3N0eWxlL1NtYWxsVmFsdWVCdWZmZXIuaAAvaG9tZS9ydW5uZXIvd29yay95b2dhL3lvZ2EvamF2YXNjcmlwdC8uLi95b2dhL3N0eWxlL1N0eWxlVmFsdWVQb29sLmgAdW5zaWduZWQgbG9uZwBzZXRCb3hTaXppbmcAZ2V0Qm94U2l6aW5nAHN0ZDo6d3N0cmluZwBzdGQ6OnN0cmluZwBzdGQ6OnUxNnN0cmluZwBzdGQ6OnUzMnN0cmluZwBzZXRQYWRkaW5nAGdldFBhZGRpbmcAZ2V0Q29tcHV0ZWRQYWRkaW5nAFRyaWVkIHRvIGNvbnN0cnVjdCBZR05vZGUgd2l0aCBudWxsIGNvbmZpZwBBdHRlbXB0aW5nIHRvIGNvbnN0cnVjdCBOb2RlIHdpdGggbnVsbCBjb25maWcAY3JlYXRlV2l0aENvbmZpZwBpbmYAc2V0QWxpZ25TZWxmAGdldEFsaWduU2VsZgBTaXplAHZhbHVlAFZhbHVlAGNyZWF0ZQBtZWFzdXJlAHNldFBvc2l0aW9uVHlwZQBnZXRQb3NpdGlvblR5cGUAaXNSZWZlcmVuY2VCYXNlbGluZQBzZXRJc1JlZmVyZW5jZUJhc2VsaW5lAGNvcHlTdHlsZQBkb3VibGUATm9kZQBleHRlbmQAaW5zZXJ0Q2hpbGQAZ2V0Q2hpbGQAcmVtb3ZlQ2hpbGQAdm9pZABzZXRFeHBlcmltZW50YWxGZWF0dXJlRW5hYmxlZABpc0V4cGVyaW1lbnRhbEZlYXR1cmVFbmFibGVkAGRpcnRpZWQAQ2Fubm90IHJlc2V0IGEgbm9kZSB3aGljaCBzdGlsbCBoYXMgY2hpbGRyZW4gYXR0YWNoZWQAdW5zZXRNZWFzdXJlRnVuYwB1bnNldERpcnRpZWRGdW5jAHNldEVycmF0YQBnZXRFcnJhdGEATWVhc3VyZSBmdW5jdGlvbiByZXR1cm5lZCBhbiBpbnZhbGlkIGRpbWVuc2lvbiB0byBZb2dhOiBbd2lkdGg9JWYsIGhlaWdodD0lZl0ARXhwZWN0IGN1c3RvbSBiYXNlbGluZSBmdW5jdGlvbiB0byBub3QgcmV0dXJuIE5hTgBOQU4ASU5GAGVtc2NyaXB0ZW46Om1lbW9yeV92aWV3PHNob3J0PgBlbXNjcmlwdGVuOjptZW1vcnlfdmlldzx1bnNpZ25lZCBzaG9ydD4AZW1zY3JpcHRlbjo6bWVtb3J5X3ZpZXc8aW50PgBlbXNjcmlwdGVuOjptZW1vcnlfdmlldzx1bnNpZ25lZCBpbnQ+AGVtc2NyaXB0ZW46Om1lbW9yeV92aWV3PGZsb2F0PgBlbXNjcmlwdGVuOjptZW1vcnlfdmlldzx1aW50OF90PgBlbXNjcmlwdGVuOjptZW1vcnlfdmlldzxpbnQ4X3Q+AGVtc2NyaXB0ZW46Om1lbW9yeV92aWV3PHVpbnQxNl90PgBlbXNjcmlwdGVuOjptZW1vcnlfdmlldzxpbnQxNl90PgBlbXNjcmlwdGVuOjptZW1vcnlfdmlldzx1aW50MzJfdD4AZW1zY3JpcHRlbjo6bWVtb3J5X3ZpZXc8aW50MzJfdD4AZW1zY3JpcHRlbjo6bWVtb3J5X3ZpZXc8Y2hhcj4AZW1zY3JpcHRlbjo6bWVtb3J5X3ZpZXc8dW5zaWduZWQgY2hhcj4Ac3RkOjpiYXNpY19zdHJpbmc8dW5zaWduZWQgY2hhcj4AZW1zY3JpcHRlbjo6bWVtb3J5X3ZpZXc8c2lnbmVk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";
    if (!ua(H)) {
      var va = H;
      H = h.locateFile ? h.locateFile(va, q) : q + va;
    }
    function wa() {
      var a = H;
      try {
        if (a == H && w) return new Uint8Array(w);
        if (ua(a)) try {
          var b = xa(a.slice(37)), c = new Uint8Array(b.length);
          for (a = 0; a < b.length; ++a) c[a] = b.charCodeAt(a);
          var d = c;
        } catch (f) {
          throw Error("Converting base64 string to bytes failed.");
        }
        else d = void 0;
        var e = d;
        if (e) return e;
        throw "both async and sync fetching of the wasm failed";
      } catch (f) {
        x(f);
      }
    }
    function ya() {
      return w || "function" != typeof fetch ? Promise.resolve().then(function() {
        return wa();
      }) : fetch(H, { credentials: "same-origin" }).then(function(a) {
        if (!a.ok) throw "failed to load wasm binary file at '" + H + "'";
        return a.arrayBuffer();
      }).catch(function() {
        return wa();
      });
    }
    function za(a) {
      for (; 0 < a.length; ) a.shift()(h);
    }
    function Aa(a) {
      if (void 0 === a) return "_unknown";
      a = a.replace(/[^a-zA-Z0-9_]/g, "$");
      var b = a.charCodeAt(0);
      return 48 <= b && 57 >= b ? "_" + a : a;
    }
    function Ba(a, b) {
      a = Aa(a);
      return function() {
        return b.apply(this, arguments);
      };
    }
    var J = [{}, { value: void 0 }, { value: null }, { value: true }, { value: false }], Ca = [];
    function Da(a) {
      var b = Error, c = Ba(a, function(d) {
        this.name = a;
        this.message = d;
        d = Error(d).stack;
        void 0 !== d && (this.stack = this.toString() + "\n" + d.replace(/^Error(:[^\n]*)?\n/, ""));
      });
      c.prototype = Object.create(b.prototype);
      c.prototype.constructor = c;
      c.prototype.toString = function() {
        return void 0 === this.message ? this.name : this.name + ": " + this.message;
      };
      return c;
    }
    var K = void 0;
    function L(a) {
      throw new K(a);
    }
    var M = (a) => {
      a || L("Cannot use deleted val. handle = " + a);
      return J[a].value;
    }, Ea = (a) => {
      switch (a) {
        case void 0:
          return 1;
        case null:
          return 2;
        case true:
          return 3;
        case false:
          return 4;
        default:
          var b = Ca.length ? Ca.pop() : J.length;
          J[b] = { ga: 1, value: a };
          return b;
      }
    }, Fa = void 0, Ga = void 0;
    function N(a) {
      for (var b = ""; A[a]; ) b += Ga[A[a++]];
      return b;
    }
    var O = [];
    function Ha() {
      for (; O.length; ) {
        var a = O.pop();
        a.M.$ = false;
        a["delete"]();
      }
    }
    var P = void 0, Q = {};
    function Ia(a, b) {
      for (void 0 === b && L("ptr should not be undefined"); a.R; ) b = a.ba(b), a = a.R;
      return b;
    }
    var R = {};
    function Ja(a) {
      a = Ka(a);
      var b = N(a);
      S(a);
      return b;
    }
    function La(a, b) {
      var c = R[a];
      void 0 === c && L(b + " has unknown type " + Ja(a));
      return c;
    }
    function Ma() {
    }
    var Na = false;
    function Oa(a) {
      --a.count.value;
      0 === a.count.value && (a.T ? a.U.W(a.T) : a.P.N.W(a.O));
    }
    function Pa(a, b, c) {
      if (b === c) return a;
      if (void 0 === c.R) return null;
      a = Pa(a, b, c.R);
      return null === a ? null : c.na(a);
    }
    var Qa = {};
    function Ra(a, b) {
      b = Ia(a, b);
      return Q[b];
    }
    var Sa = void 0;
    function Ta(a) {
      throw new Sa(a);
    }
    function Ua(a, b) {
      b.P && b.O || Ta("makeClassHandle requires ptr and ptrType");
      !!b.U !== !!b.T && Ta("Both smartPtrType and smartPtr must be specified");
      b.count = { value: 1 };
      return T(Object.create(a, { M: { value: b } }));
    }
    function T(a) {
      if ("undefined" === typeof FinalizationRegistry) return T = (b) => b, a;
      Na = new FinalizationRegistry((b) => {
        Oa(b.M);
      });
      T = (b) => {
        var c = b.M;
        c.T && Na.register(b, { M: c }, b);
        return b;
      };
      Ma = (b) => {
        Na.unregister(b);
      };
      return T(a);
    }
    var Va = {};
    function Wa(a) {
      for (; a.length; ) {
        var b = a.pop();
        a.pop()(b);
      }
    }
    function Xa(a) {
      return this.fromWireType(D[a >> 2]);
    }
    var U = {}, Ya = {};
    function V(a, b, c) {
      function d(k) {
        k = c(k);
        k.length !== a.length && Ta("Mismatched type converter count");
        for (var m = 0; m < a.length; ++m) W(a[m], k[m]);
      }
      a.forEach(function(k) {
        Ya[k] = b;
      });
      var e = Array(b.length), f = [], g = 0;
      b.forEach((k, m) => {
        R.hasOwnProperty(k) ? e[m] = R[k] : (f.push(k), U.hasOwnProperty(k) || (U[k] = []), U[k].push(() => {
          e[m] = R[k];
          ++g;
          g === f.length && d(e);
        }));
      });
      0 === f.length && d(e);
    }
    function Za(a) {
      switch (a) {
        case 1:
          return 0;
        case 2:
          return 1;
        case 4:
          return 2;
        case 8:
          return 3;
        default:
          throw new TypeError("Unknown type size: " + a);
      }
    }
    function W(a, b, c = {}) {
      if (!("argPackAdvance" in b)) throw new TypeError("registerType registeredInstance requires argPackAdvance");
      var d = b.name;
      a || L('type "' + d + '" must have a positive integer typeid pointer');
      if (R.hasOwnProperty(a)) {
        if (c.ua) return;
        L("Cannot register type '" + d + "' twice");
      }
      R[a] = b;
      delete Ya[a];
      U.hasOwnProperty(a) && (b = U[a], delete U[a], b.forEach((e) => e()));
    }
    function $a(a) {
      L(a.M.P.N.name + " instance already deleted");
    }
    function X() {
    }
    function ab(a, b, c) {
      if (void 0 === a[b].S) {
        var d = a[b];
        a[b] = function() {
          a[b].S.hasOwnProperty(arguments.length) || L("Function '" + c + "' called with an invalid number of arguments (" + arguments.length + ") - expects one of (" + a[b].S + ")!");
          return a[b].S[arguments.length].apply(this, arguments);
        };
        a[b].S = [];
        a[b].S[d.Z] = d;
      }
    }
    function bb(a, b) {
      h.hasOwnProperty(a) ? (L("Cannot register public name '" + a + "' twice"), ab(h, a, a), h.hasOwnProperty(void 0) && L("Cannot register multiple overloads of a function with the same number of arguments (undefined)!"), h[a].S[void 0] = b) : h[a] = b;
    }
    function cb(a, b, c, d, e, f, g, k) {
      this.name = a;
      this.constructor = b;
      this.X = c;
      this.W = d;
      this.R = e;
      this.pa = f;
      this.ba = g;
      this.na = k;
      this.ja = [];
    }
    function db(a, b, c) {
      for (; b !== c; ) b.ba || L("Expected null or instance of " + c.name + ", got an instance of " + b.name), a = b.ba(a), b = b.R;
      return a;
    }
    function eb(a, b) {
      if (null === b) return this.ea && L("null is not a valid " + this.name), 0;
      b.M || L('Cannot pass "' + fb(b) + '" as a ' + this.name);
      b.M.O || L("Cannot pass deleted object as a pointer of type " + this.name);
      return db(b.M.O, b.M.P.N, this.N);
    }
    function gb(a, b) {
      if (null === b) {
        this.ea && L("null is not a valid " + this.name);
        if (this.da) {
          var c = this.fa();
          null !== a && a.push(this.W, c);
          return c;
        }
        return 0;
      }
      b.M || L('Cannot pass "' + fb(b) + '" as a ' + this.name);
      b.M.O || L("Cannot pass deleted object as a pointer of type " + this.name);
      !this.ca && b.M.P.ca && L("Cannot convert argument of type " + (b.M.U ? b.M.U.name : b.M.P.name) + " to parameter type " + this.name);
      c = db(b.M.O, b.M.P.N, this.N);
      if (this.da) switch (void 0 === b.M.T && L("Passing raw pointer to smart pointer is illegal"), this.Ba) {
        case 0:
          b.M.U === this ? c = b.M.T : L("Cannot convert argument of type " + (b.M.U ? b.M.U.name : b.M.P.name) + " to parameter type " + this.name);
          break;
        case 1:
          c = b.M.T;
          break;
        case 2:
          if (b.M.U === this) c = b.M.T;
          else {
            var d = b.clone();
            c = this.xa(c, Ea(function() {
              d["delete"]();
            }));
            null !== a && a.push(this.W, c);
          }
          break;
        default:
          L("Unsupporting sharing policy");
      }
      return c;
    }
    function hb(a, b) {
      if (null === b) return this.ea && L("null is not a valid " + this.name), 0;
      b.M || L('Cannot pass "' + fb(b) + '" as a ' + this.name);
      b.M.O || L("Cannot pass deleted object as a pointer of type " + this.name);
      b.M.P.ca && L("Cannot convert argument of type " + b.M.P.name + " to parameter type " + this.name);
      return db(b.M.O, b.M.P.N, this.N);
    }
    function Y(a, b, c, d) {
      this.name = a;
      this.N = b;
      this.ea = c;
      this.ca = d;
      this.da = false;
      this.W = this.xa = this.fa = this.ka = this.Ba = this.wa = void 0;
      void 0 !== b.R ? this.toWireType = gb : (this.toWireType = d ? eb : hb, this.V = null);
    }
    function ib(a, b) {
      h.hasOwnProperty(a) || Ta("Replacing nonexistant public symbol");
      h[a] = b;
      h[a].Z = void 0;
    }
    function jb(a, b) {
      var c = [];
      return function() {
        c.length = 0;
        Object.assign(c, arguments);
        if (a.includes("j")) {
          var d = h["dynCall_" + a];
          d = c && c.length ? d.apply(null, [b].concat(c)) : d.call(null, b);
        } else d = oa.get(b).apply(null, c);
        return d;
      };
    }
    function Z(a, b) {
      a = N(a);
      var c = a.includes("j") ? jb(a, b) : oa.get(b);
      "function" != typeof c && L("unknown function pointer with signature " + a + ": " + b);
      return c;
    }
    var mb = void 0;
    function nb(a, b) {
      function c(f) {
        e[f] || R[f] || (Ya[f] ? Ya[f].forEach(c) : (d.push(f), e[f] = true));
      }
      var d = [], e = {};
      b.forEach(c);
      throw new mb(a + ": " + d.map(Ja).join([", "]));
    }
    function ob(a, b, c, d, e) {
      var f = b.length;
      2 > f && L("argTypes array size mismatch! Must at least get return value and 'this' types!");
      var g = null !== b[1] && null !== c, k = false;
      for (c = 1; c < b.length; ++c) if (null !== b[c] && void 0 === b[c].V) {
        k = true;
        break;
      }
      var m = "void" !== b[0].name, l = f - 2, n = Array(l), p = [], r = [];
      return function() {
        arguments.length !== l && L("function " + a + " called with " + arguments.length + " arguments, expected " + l + " args!");
        r.length = 0;
        p.length = g ? 2 : 1;
        p[0] = e;
        if (g) {
          var u = b[1].toWireType(r, this);
          p[1] = u;
        }
        for (var t = 0; t < l; ++t) n[t] = b[t + 2].toWireType(r, arguments[t]), p.push(n[t]);
        t = d.apply(null, p);
        if (k) Wa(r);
        else for (var y = g ? 1 : 2; y < b.length; y++) {
          var B = 1 === y ? u : n[y - 2];
          null !== b[y].V && b[y].V(B);
        }
        u = m ? b[0].fromWireType(t) : void 0;
        return u;
      };
    }
    function pb(a, b) {
      for (var c = [], d = 0; d < a; d++) c.push(E[b + 4 * d >> 2]);
      return c;
    }
    function qb(a) {
      4 < a && 0 === --J[a].ga && (J[a] = void 0, Ca.push(a));
    }
    function fb(a) {
      if (null === a) return "null";
      var b = typeof a;
      return "object" === b || "array" === b || "function" === b ? a.toString() : "" + a;
    }
    function rb(a, b) {
      switch (b) {
        case 2:
          return function(c) {
            return this.fromWireType(la[c >> 2]);
          };
        case 3:
          return function(c) {
            return this.fromWireType(ma[c >> 3]);
          };
        default:
          throw new TypeError("Unknown float type: " + a);
      }
    }
    function sb(a, b, c) {
      switch (b) {
        case 0:
          return c ? function(d) {
            return ja[d];
          } : function(d) {
            return A[d];
          };
        case 1:
          return c ? function(d) {
            return C[d >> 1];
          } : function(d) {
            return ka[d >> 1];
          };
        case 2:
          return c ? function(d) {
            return D[d >> 2];
          } : function(d) {
            return E[d >> 2];
          };
        default:
          throw new TypeError("Unknown integer type: " + a);
      }
    }
    function tb(a, b) {
      for (var c = "", d = 0; !(d >= b / 2); ++d) {
        var e = C[a + 2 * d >> 1];
        if (0 == e) break;
        c += String.fromCharCode(e);
      }
      return c;
    }
    function ub(a, b, c) {
      void 0 === c && (c = 2147483647);
      if (2 > c) return 0;
      c -= 2;
      var d = b;
      c = c < 2 * a.length ? c / 2 : a.length;
      for (var e = 0; e < c; ++e) C[b >> 1] = a.charCodeAt(e), b += 2;
      C[b >> 1] = 0;
      return b - d;
    }
    function vb(a) {
      return 2 * a.length;
    }
    function wb(a, b) {
      for (var c = 0, d = ""; !(c >= b / 4); ) {
        var e = D[a + 4 * c >> 2];
        if (0 == e) break;
        ++c;
        65536 <= e ? (e -= 65536, d += String.fromCharCode(55296 | e >> 10, 56320 | e & 1023)) : d += String.fromCharCode(e);
      }
      return d;
    }
    function xb(a, b, c) {
      void 0 === c && (c = 2147483647);
      if (4 > c) return 0;
      var d = b;
      c = d + c - 4;
      for (var e = 0; e < a.length; ++e) {
        var f = a.charCodeAt(e);
        if (55296 <= f && 57343 >= f) {
          var g = a.charCodeAt(++e);
          f = 65536 + ((f & 1023) << 10) | g & 1023;
        }
        D[b >> 2] = f;
        b += 4;
        if (b + 4 > c) break;
      }
      D[b >> 2] = 0;
      return b - d;
    }
    function yb(a) {
      for (var b = 0, c = 0; c < a.length; ++c) {
        var d = a.charCodeAt(c);
        55296 <= d && 57343 >= d && ++c;
        b += 4;
      }
      return b;
    }
    var zb = {};
    function Ab(a) {
      var b = zb[a];
      return void 0 === b ? N(a) : b;
    }
    var Bb = [];
    function Cb(a) {
      var b = Bb.length;
      Bb.push(a);
      return b;
    }
    function Db(a, b) {
      for (var c = Array(a), d = 0; d < a; ++d) c[d] = La(E[b + 4 * d >> 2], "parameter " + d);
      return c;
    }
    var Eb = [], Fb = [null, [], []];
    K = h.BindingError = Da("BindingError");
    h.count_emval_handles = function() {
      for (var a = 0, b = 5; b < J.length; ++b) void 0 !== J[b] && ++a;
      return a;
    };
    h.get_first_emval = function() {
      for (var a = 5; a < J.length; ++a) if (void 0 !== J[a]) return J[a];
      return null;
    };
    Fa = h.PureVirtualError = Da("PureVirtualError");
    for (var Gb = Array(256), Hb = 0; 256 > Hb; ++Hb) Gb[Hb] = String.fromCharCode(Hb);
    Ga = Gb;
    h.getInheritedInstanceCount = function() {
      return Object.keys(Q).length;
    };
    h.getLiveInheritedInstances = function() {
      var a = [], b;
      for (b in Q) Q.hasOwnProperty(b) && a.push(Q[b]);
      return a;
    };
    h.flushPendingDeletes = Ha;
    h.setDelayFunction = function(a) {
      P = a;
      O.length && P && P(Ha);
    };
    Sa = h.InternalError = Da("InternalError");
    X.prototype.isAliasOf = function(a) {
      if (!(this instanceof X && a instanceof X)) return false;
      var b = this.M.P.N, c = this.M.O, d = a.M.P.N;
      for (a = a.M.O; b.R; ) c = b.ba(c), b = b.R;
      for (; d.R; ) a = d.ba(a), d = d.R;
      return b === d && c === a;
    };
    X.prototype.clone = function() {
      this.M.O || $a(this);
      if (this.M.aa) return this.M.count.value += 1, this;
      var a = T, b = Object, c = b.create, d = Object.getPrototypeOf(this), e = this.M;
      a = a(c.call(b, d, { M: { value: { count: e.count, $: e.$, aa: e.aa, O: e.O, P: e.P, T: e.T, U: e.U } } }));
      a.M.count.value += 1;
      a.M.$ = false;
      return a;
    };
    X.prototype["delete"] = function() {
      this.M.O || $a(this);
      this.M.$ && !this.M.aa && L("Object already scheduled for deletion");
      Ma(this);
      Oa(this.M);
      this.M.aa || (this.M.T = void 0, this.M.O = void 0);
    };
    X.prototype.isDeleted = function() {
      return !this.M.O;
    };
    X.prototype.deleteLater = function() {
      this.M.O || $a(this);
      this.M.$ && !this.M.aa && L("Object already scheduled for deletion");
      O.push(this);
      1 === O.length && P && P(Ha);
      this.M.$ = true;
      return this;
    };
    Y.prototype.qa = function(a) {
      this.ka && (a = this.ka(a));
      return a;
    };
    Y.prototype.ha = function(a) {
      this.W && this.W(a);
    };
    Y.prototype.argPackAdvance = 8;
    Y.prototype.readValueFromPointer = Xa;
    Y.prototype.deleteObject = function(a) {
      if (null !== a) a["delete"]();
    };
    Y.prototype.fromWireType = function(a) {
      function b() {
        return this.da ? Ua(this.N.X, { P: this.wa, O: c, U: this, T: a }) : Ua(this.N.X, { P: this, O: a });
      }
      var c = this.qa(a);
      if (!c) return this.ha(a), null;
      var d = Ra(this.N, c);
      if (void 0 !== d) {
        if (0 === d.M.count.value) return d.M.O = c, d.M.T = a, d.clone();
        d = d.clone();
        this.ha(a);
        return d;
      }
      d = this.N.pa(c);
      d = Qa[d];
      if (!d) return b.call(this);
      d = this.ca ? d.la : d.pointerType;
      var e = Pa(c, this.N, d.N);
      return null === e ? b.call(this) : this.da ? Ua(d.N.X, { P: d, O: e, U: this, T: a }) : Ua(d.N.X, { P: d, O: e });
    };
    mb = h.UnboundTypeError = Da("UnboundTypeError");
    var xa = "function" == typeof atob ? atob : function(a) {
      var b = "", c = 0;
      a = a.replace(/[^A-Za-z0-9\+\/=]/g, "");
      do {
        var d = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=".indexOf(a.charAt(c++));
        var e = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=".indexOf(a.charAt(c++));
        var f = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=".indexOf(a.charAt(c++));
        var g = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=".indexOf(a.charAt(c++));
        d = d << 2 | e >> 4;
        e = (e & 15) << 4 | f >> 2;
        var k = (f & 3) << 6 | g;
        b += String.fromCharCode(d);
        64 !== f && (b += String.fromCharCode(e));
        64 !== g && (b += String.fromCharCode(k));
      } while (c < a.length);
      return b;
    }, Jb = {
      l: function(a, b, c, d) {
        x("Assertion failed: " + (a ? z(A, a) : "") + ", at: " + [b ? b ? z(A, b) : "" : "unknown filename", c, d ? d ? z(A, d) : "" : "unknown function"]);
      },
      q: function(a, b, c) {
        a = N(a);
        b = La(b, "wrapper");
        c = M(c);
        var d = [].slice, e = b.N, f = e.X, g = e.R.X, k = e.R.constructor;
        a = Ba(a, function() {
          e.R.ja.forEach(function(l) {
            if (this[l] === g[l]) throw new Fa("Pure virtual function " + l + " must be implemented in JavaScript");
          }.bind(this));
          Object.defineProperty(this, "__parent", { value: f });
          this.__construct.apply(this, d.call(arguments));
        });
        f.__construct = function() {
          this === f && L("Pass correct 'this' to __construct");
          var l = k.implement.apply(void 0, [this].concat(d.call(arguments)));
          Ma(l);
          var n = l.M;
          l.notifyOnDestruction();
          n.aa = true;
          Object.defineProperties(this, { M: { value: n } });
          T(this);
          l = n.O;
          l = Ia(e, l);
          Q.hasOwnProperty(l) ? L("Tried to register registered instance: " + l) : Q[l] = this;
        };
        f.__destruct = function() {
          this === f && L("Pass correct 'this' to __destruct");
          Ma(this);
          var l = this.M.O;
          l = Ia(e, l);
          Q.hasOwnProperty(l) ? delete Q[l] : L("Tried to unregister unregistered instance: " + l);
        };
        a.prototype = Object.create(f);
        for (var m in c) a.prototype[m] = c[m];
        return Ea(a);
      },
      j: function(a) {
        var b = Va[a];
        delete Va[a];
        var c = b.fa, d = b.W, e = b.ia, f = e.map((g) => g.ta).concat(e.map((g) => g.za));
        V([a], f, (g) => {
          var k = {};
          e.forEach((m, l) => {
            var n = g[l], p = m.ra, r = m.sa, u = g[l + e.length], t = m.ya, y = m.Aa;
            k[m.oa] = { read: (B) => n.fromWireType(p(r, B)), write: (B, ba) => {
              var I = [];
              t(
                y,
                B,
                u.toWireType(I, ba)
              );
              Wa(I);
            } };
          });
          return [{ name: b.name, fromWireType: function(m) {
            var l = {}, n;
            for (n in k) l[n] = k[n].read(m);
            d(m);
            return l;
          }, toWireType: function(m, l) {
            for (var n in k) if (!(n in l)) throw new TypeError('Missing field:  "' + n + '"');
            var p = c();
            for (n in k) k[n].write(p, l[n]);
            null !== m && m.push(d, p);
            return p;
          }, argPackAdvance: 8, readValueFromPointer: Xa, V: d }];
        });
      },
      v: function() {
      },
      B: function(a, b, c, d, e) {
        var f = Za(c);
        b = N(b);
        W(a, {
          name: b,
          fromWireType: function(g) {
            return !!g;
          },
          toWireType: function(g, k) {
            return k ? d : e;
          },
          argPackAdvance: 8,
          readValueFromPointer: function(g) {
            if (1 === c) var k = ja;
            else if (2 === c) k = C;
            else if (4 === c) k = D;
            else throw new TypeError("Unknown boolean type size: " + b);
            return this.fromWireType(k[g >> f]);
          },
          V: null
        });
      },
      f: function(a, b, c, d, e, f, g, k, m, l, n, p, r) {
        n = N(n);
        f = Z(e, f);
        k && (k = Z(g, k));
        l && (l = Z(m, l));
        r = Z(p, r);
        var u = Aa(n);
        bb(u, function() {
          nb("Cannot construct " + n + " due to unbound types", [d]);
        });
        V([a, b, c], d ? [d] : [], function(t) {
          t = t[0];
          if (d) {
            var y = t.N;
            var B = y.X;
          } else B = X.prototype;
          t = Ba(u, function() {
            if (Object.getPrototypeOf(this) !== ba) throw new K("Use 'new' to construct " + n);
            if (void 0 === I.Y) throw new K(n + " has no accessible constructor");
            var kb = I.Y[arguments.length];
            if (void 0 === kb) throw new K("Tried to invoke ctor of " + n + " with invalid number of parameters (" + arguments.length + ") - expected (" + Object.keys(I.Y).toString() + ") parameters instead!");
            return kb.apply(this, arguments);
          });
          var ba = Object.create(B, { constructor: { value: t } });
          t.prototype = ba;
          var I = new cb(n, t, ba, r, y, f, k, l);
          y = new Y(n, I, true, false);
          B = new Y(n + "*", I, false, false);
          var lb = new Y(n + " const*", I, false, true);
          Qa[a] = {
            pointerType: B,
            la: lb
          };
          ib(u, t);
          return [y, B, lb];
        });
      },
      d: function(a, b, c, d, e, f, g) {
        var k = pb(c, d);
        b = N(b);
        f = Z(e, f);
        V([], [a], function(m) {
          function l() {
            nb("Cannot call " + n + " due to unbound types", k);
          }
          m = m[0];
          var n = m.name + "." + b;
          b.startsWith("@@") && (b = Symbol[b.substring(2)]);
          var p = m.N.constructor;
          void 0 === p[b] ? (l.Z = c - 1, p[b] = l) : (ab(p, b, n), p[b].S[c - 1] = l);
          V([], k, function(r) {
            r = ob(n, [r[0], null].concat(r.slice(1)), null, f, g);
            void 0 === p[b].S ? (r.Z = c - 1, p[b] = r) : p[b].S[c - 1] = r;
            return [];
          });
          return [];
        });
      },
      p: function(a, b, c, d, e, f) {
        0 < b || x();
        var g = pb(
          b,
          c
        );
        e = Z(d, e);
        V([], [a], function(k) {
          k = k[0];
          var m = "constructor " + k.name;
          void 0 === k.N.Y && (k.N.Y = []);
          if (void 0 !== k.N.Y[b - 1]) throw new K("Cannot register multiple constructors with identical number of parameters (" + (b - 1) + ") for class '" + k.name + "'! Overload resolution is currently only performed using the parameter count, not actual type info!");
          k.N.Y[b - 1] = () => {
            nb("Cannot construct " + k.name + " due to unbound types", g);
          };
          V([], g, function(l) {
            l.splice(1, 0, null);
            k.N.Y[b - 1] = ob(m, l, null, e, f);
            return [];
          });
          return [];
        });
      },
      a: function(a, b, c, d, e, f, g, k) {
        var m = pb(c, d);
        b = N(b);
        f = Z(e, f);
        V([], [a], function(l) {
          function n() {
            nb("Cannot call " + p + " due to unbound types", m);
          }
          l = l[0];
          var p = l.name + "." + b;
          b.startsWith("@@") && (b = Symbol[b.substring(2)]);
          k && l.N.ja.push(b);
          var r = l.N.X, u = r[b];
          void 0 === u || void 0 === u.S && u.className !== l.name && u.Z === c - 2 ? (n.Z = c - 2, n.className = l.name, r[b] = n) : (ab(r, b, p), r[b].S[c - 2] = n);
          V([], m, function(t) {
            t = ob(p, t, l, f, g);
            void 0 === r[b].S ? (t.Z = c - 2, r[b] = t) : r[b].S[c - 2] = t;
            return [];
          });
          return [];
        });
      },
      A: function(a, b) {
        b = N(b);
        W(
          a,
          { name: b, fromWireType: function(c) {
            var d = M(c);
            qb(c);
            return d;
          }, toWireType: function(c, d) {
            return Ea(d);
          }, argPackAdvance: 8, readValueFromPointer: Xa, V: null }
        );
      },
      n: function(a, b, c) {
        c = Za(c);
        b = N(b);
        W(a, { name: b, fromWireType: function(d) {
          return d;
        }, toWireType: function(d, e) {
          return e;
        }, argPackAdvance: 8, readValueFromPointer: rb(b, c), V: null });
      },
      e: function(a, b, c, d, e) {
        b = N(b);
        -1 === e && (e = 4294967295);
        e = Za(c);
        var f = (k) => k;
        if (0 === d) {
          var g = 32 - 8 * c;
          f = (k) => k << g >>> g;
        }
        c = b.includes("unsigned") ? function(k, m) {
          return m >>> 0;
        } : function(k, m) {
          return m;
        };
        W(a, { name: b, fromWireType: f, toWireType: c, argPackAdvance: 8, readValueFromPointer: sb(b, e, 0 !== d), V: null });
      },
      b: function(a, b, c) {
        function d(f) {
          f >>= 2;
          var g = E;
          return new e(ia, g[f + 1], g[f]);
        }
        var e = [Int8Array, Uint8Array, Int16Array, Uint16Array, Int32Array, Uint32Array, Float32Array, Float64Array][b];
        c = N(c);
        W(a, { name: c, fromWireType: d, argPackAdvance: 8, readValueFromPointer: d }, { ua: true });
      },
      o: function(a, b) {
        b = N(b);
        var c = "std::string" === b;
        W(a, { name: b, fromWireType: function(d) {
          var e = E[d >> 2], f = d + 4;
          if (c) for (var g = f, k = 0; k <= e; ++k) {
            var m = f + k;
            if (k == e || 0 == A[m]) {
              g = g ? z(A, g, m - g) : "";
              if (void 0 === l) var l = g;
              else l += String.fromCharCode(0), l += g;
              g = m + 1;
            }
          }
          else {
            l = Array(e);
            for (k = 0; k < e; ++k) l[k] = String.fromCharCode(A[f + k]);
            l = l.join("");
          }
          S(d);
          return l;
        }, toWireType: function(d, e) {
          e instanceof ArrayBuffer && (e = new Uint8Array(e));
          var f, g = "string" == typeof e;
          g || e instanceof Uint8Array || e instanceof Uint8ClampedArray || e instanceof Int8Array || L("Cannot pass non-string to std::string");
          if (c && g) {
            var k = 0;
            for (f = 0; f < e.length; ++f) {
              var m = e.charCodeAt(f);
              127 >= m ? k++ : 2047 >= m ? k += 2 : 55296 <= m && 57343 >= m ? (k += 4, ++f) : k += 3;
            }
            f = k;
          } else f = e.length;
          k = Ib(4 + f + 1);
          m = k + 4;
          E[k >> 2] = f;
          if (c && g) {
            if (g = m, m = f + 1, f = A, 0 < m) {
              m = g + m - 1;
              for (var l = 0; l < e.length; ++l) {
                var n = e.charCodeAt(l);
                if (55296 <= n && 57343 >= n) {
                  var p = e.charCodeAt(++l);
                  n = 65536 + ((n & 1023) << 10) | p & 1023;
                }
                if (127 >= n) {
                  if (g >= m) break;
                  f[g++] = n;
                } else {
                  if (2047 >= n) {
                    if (g + 1 >= m) break;
                    f[g++] = 192 | n >> 6;
                  } else {
                    if (65535 >= n) {
                      if (g + 2 >= m) break;
                      f[g++] = 224 | n >> 12;
                    } else {
                      if (g + 3 >= m) break;
                      f[g++] = 240 | n >> 18;
                      f[g++] = 128 | n >> 12 & 63;
                    }
                    f[g++] = 128 | n >> 6 & 63;
                  }
                  f[g++] = 128 | n & 63;
                }
              }
              f[g] = 0;
            }
          } else if (g) for (g = 0; g < f; ++g) l = e.charCodeAt(g), 255 < l && (S(m), L("String has UTF-16 code units that do not fit in 8 bits")), A[m + g] = l;
          else for (g = 0; g < f; ++g) A[m + g] = e[g];
          null !== d && d.push(S, k);
          return k;
        }, argPackAdvance: 8, readValueFromPointer: Xa, V: function(d) {
          S(d);
        } });
      },
      i: function(a, b, c) {
        c = N(c);
        if (2 === b) {
          var d = tb;
          var e = ub;
          var f = vb;
          var g = () => ka;
          var k = 1;
        } else 4 === b && (d = wb, e = xb, f = yb, g = () => E, k = 2);
        W(a, { name: c, fromWireType: function(m) {
          for (var l = E[m >> 2], n = g(), p, r = m + 4, u = 0; u <= l; ++u) {
            var t = m + 4 + u * b;
            if (u == l || 0 == n[t >> k]) r = d(r, t - r), void 0 === p ? p = r : (p += String.fromCharCode(0), p += r), r = t + b;
          }
          S(m);
          return p;
        }, toWireType: function(m, l) {
          "string" != typeof l && L("Cannot pass non-string to C++ string type " + c);
          var n = f(l), p = Ib(4 + n + b);
          E[p >> 2] = n >> k;
          e(l, p + 4, n + b);
          null !== m && m.push(S, p);
          return p;
        }, argPackAdvance: 8, readValueFromPointer: Xa, V: function(m) {
          S(m);
        } });
      },
      k: function(a, b, c, d, e, f) {
        Va[a] = { name: N(b), fa: Z(c, d), W: Z(e, f), ia: [] };
      },
      h: function(a, b, c, d, e, f, g, k, m, l) {
        Va[a].ia.push({ oa: N(b), ta: c, ra: Z(d, e), sa: f, za: g, ya: Z(k, m), Aa: l });
      },
      C: function(a, b) {
        b = N(b);
        W(a, {
          va: true,
          name: b,
          argPackAdvance: 0,
          fromWireType: function() {
          },
          toWireType: function() {
          }
        });
      },
      s: function(a, b, c, d, e) {
        a = Bb[a];
        b = M(b);
        c = Ab(c);
        var f = [];
        E[d >> 2] = Ea(f);
        return a(b, c, f, e);
      },
      t: function(a, b, c, d) {
        a = Bb[a];
        b = M(b);
        c = Ab(c);
        a(b, c, null, d);
      },
      g: qb,
      m: function(a, b) {
        var c = Db(a, b), d = c[0];
        b = d.name + "_$" + c.slice(1).map(function(g) {
          return g.name;
        }).join("_") + "$";
        var e = Eb[b];
        if (void 0 !== e) return e;
        var f = Array(a - 1);
        e = Cb((g, k, m, l) => {
          for (var n = 0, p = 0; p < a - 1; ++p) f[p] = c[p + 1].readValueFromPointer(l + n), n += c[p + 1].argPackAdvance;
          g = g[k].apply(
            g,
            f
          );
          for (p = 0; p < a - 1; ++p) c[p + 1].ma && c[p + 1].ma(f[p]);
          if (!d.va) return d.toWireType(m, g);
        });
        return Eb[b] = e;
      },
      D: function(a) {
        4 < a && (J[a].ga += 1);
      },
      r: function(a) {
        var b = M(a);
        Wa(b);
        qb(a);
      },
      c: function() {
        x("");
      },
      x: function(a, b, c) {
        A.copyWithin(a, b, b + c);
      },
      w: function(a) {
        var b = A.length;
        a >>>= 0;
        if (2147483648 < a) return false;
        for (var c = 1; 4 >= c; c *= 2) {
          var d = b * (1 + 0.2 / c);
          d = Math.min(d, a + 100663296);
          var e = Math;
          d = Math.max(a, d);
          e = e.min.call(e, 2147483648, d + (65536 - d % 65536) % 65536);
          a: {
            try {
              fa.grow(e - ia.byteLength + 65535 >>> 16);
              na();
              var f = 1;
              break a;
            } catch (g) {
            }
            f = void 0;
          }
          if (f) return true;
        }
        return false;
      },
      z: function() {
        return 52;
      },
      u: function() {
        return 70;
      },
      y: function(a, b, c, d) {
        for (var e = 0, f = 0; f < c; f++) {
          var g = E[b >> 2], k = E[b + 4 >> 2];
          b += 8;
          for (var m = 0; m < k; m++) {
            var l = A[g + m], n = Fb[a];
            0 === l || 10 === l ? ((1 === a ? ea : v)(z(n, 0)), n.length = 0) : n.push(l);
          }
          e += k;
        }
        E[d >> 2] = e;
        return 0;
      }
    };
    (function() {
      function a(e) {
        h.asm = e.exports;
        fa = h.asm.E;
        na();
        oa = h.asm.J;
        qa.unshift(h.asm.F);
        F--;
        h.monitorRunDependencies && h.monitorRunDependencies(F);
        0 == F && (null !== ta && (clearInterval(ta), ta = null), G && (e = G, G = null, e()));
      }
      function b(e) {
        a(e.instance);
      }
      function c(e) {
        return ya().then(function(f) {
          return WebAssembly.instantiate(f, d);
        }).then(function(f) {
          return f;
        }).then(e, function(f) {
          v("failed to asynchronously prepare wasm: " + f);
          x(f);
        });
      }
      var d = { a: Jb };
      F++;
      h.monitorRunDependencies && h.monitorRunDependencies(F);
      if (h.instantiateWasm) try {
        return h.instantiateWasm(
          d,
          a
        );
      } catch (e) {
        v("Module.instantiateWasm callback failed with error: " + e), ca(e);
      }
      (function() {
        return w || "function" != typeof WebAssembly.instantiateStreaming || ua(H) || "function" != typeof fetch ? c(b) : fetch(H, { credentials: "same-origin" }).then(function(e) {
          return WebAssembly.instantiateStreaming(e, d).then(b, function(f) {
            v("wasm streaming compile failed: " + f);
            v("falling back to ArrayBuffer instantiation");
            return c(b);
          });
        });
      })().catch(ca);
      return {};
    })();
    h.___wasm_call_ctors = function() {
      return (h.___wasm_call_ctors = h.asm.F).apply(null, arguments);
    };
    var Ka = h.___getTypeName = function() {
      return (Ka = h.___getTypeName = h.asm.G).apply(null, arguments);
    };
    h.__embind_initialize_bindings = function() {
      return (h.__embind_initialize_bindings = h.asm.H).apply(null, arguments);
    };
    var Ib = h._malloc = function() {
      return (Ib = h._malloc = h.asm.I).apply(null, arguments);
    }, S = h._free = function() {
      return (S = h._free = h.asm.K).apply(null, arguments);
    };
    h.dynCall_jiji = function() {
      return (h.dynCall_jiji = h.asm.L).apply(null, arguments);
    };
    var Kb;
    G = function Lb() {
      Kb || Mb();
      Kb || (G = Lb);
    };
    function Mb() {
      function a() {
        if (!Kb && (Kb = true, h.calledRun = true, !ha)) {
          za(qa);
          aa(h);
          if (h.onRuntimeInitialized) h.onRuntimeInitialized();
          if (h.postRun) for ("function" == typeof h.postRun && (h.postRun = [h.postRun]); h.postRun.length; ) {
            var b = h.postRun.shift();
            ra.unshift(b);
          }
          za(ra);
        }
      }
      if (!(0 < F)) {
        if (h.preRun) for ("function" == typeof h.preRun && (h.preRun = [h.preRun]); h.preRun.length; ) sa();
        za(pa);
        0 < F || (h.setStatus ? (h.setStatus("Running..."), setTimeout(function() {
          setTimeout(function() {
            h.setStatus("");
          }, 1);
          a();
        }, 1)) : a());
      }
    }
    if (h.preInit) for ("function" == typeof h.preInit && (h.preInit = [h.preInit]); 0 < h.preInit.length; ) h.preInit.pop()();
    Mb();
    return loadYoga2.ready;
  };
})();
var yoga_wasm_base64_esm_default = loadYoga;

// node_modules/yoga-layout/dist/src/generated/YGEnums.js
var Align = /* @__PURE__ */ function(Align2) {
  Align2[Align2["Auto"] = 0] = "Auto";
  Align2[Align2["FlexStart"] = 1] = "FlexStart";
  Align2[Align2["Center"] = 2] = "Center";
  Align2[Align2["FlexEnd"] = 3] = "FlexEnd";
  Align2[Align2["Stretch"] = 4] = "Stretch";
  Align2[Align2["Baseline"] = 5] = "Baseline";
  Align2[Align2["SpaceBetween"] = 6] = "SpaceBetween";
  Align2[Align2["SpaceAround"] = 7] = "SpaceAround";
  Align2[Align2["SpaceEvenly"] = 8] = "SpaceEvenly";
  return Align2;
}({});
var BoxSizing = /* @__PURE__ */ function(BoxSizing2) {
  BoxSizing2[BoxSizing2["BorderBox"] = 0] = "BorderBox";
  BoxSizing2[BoxSizing2["ContentBox"] = 1] = "ContentBox";
  return BoxSizing2;
}({});
var Dimension = /* @__PURE__ */ function(Dimension2) {
  Dimension2[Dimension2["Width"] = 0] = "Width";
  Dimension2[Dimension2["Height"] = 1] = "Height";
  return Dimension2;
}({});
var Direction = /* @__PURE__ */ function(Direction2) {
  Direction2[Direction2["Inherit"] = 0] = "Inherit";
  Direction2[Direction2["LTR"] = 1] = "LTR";
  Direction2[Direction2["RTL"] = 2] = "RTL";
  return Direction2;
}({});
var Display = /* @__PURE__ */ function(Display2) {
  Display2[Display2["Flex"] = 0] = "Flex";
  Display2[Display2["None"] = 1] = "None";
  Display2[Display2["Contents"] = 2] = "Contents";
  return Display2;
}({});
var Edge = /* @__PURE__ */ function(Edge2) {
  Edge2[Edge2["Left"] = 0] = "Left";
  Edge2[Edge2["Top"] = 1] = "Top";
  Edge2[Edge2["Right"] = 2] = "Right";
  Edge2[Edge2["Bottom"] = 3] = "Bottom";
  Edge2[Edge2["Start"] = 4] = "Start";
  Edge2[Edge2["End"] = 5] = "End";
  Edge2[Edge2["Horizontal"] = 6] = "Horizontal";
  Edge2[Edge2["Vertical"] = 7] = "Vertical";
  Edge2[Edge2["All"] = 8] = "All";
  return Edge2;
}({});
var Errata = /* @__PURE__ */ function(Errata2) {
  Errata2[Errata2["None"] = 0] = "None";
  Errata2[Errata2["StretchFlexBasis"] = 1] = "StretchFlexBasis";
  Errata2[Errata2["AbsolutePositionWithoutInsetsExcludesPadding"] = 2] = "AbsolutePositionWithoutInsetsExcludesPadding";
  Errata2[Errata2["AbsolutePercentAgainstInnerSize"] = 4] = "AbsolutePercentAgainstInnerSize";
  Errata2[Errata2["All"] = 2147483647] = "All";
  Errata2[Errata2["Classic"] = 2147483646] = "Classic";
  return Errata2;
}({});
var ExperimentalFeature = /* @__PURE__ */ function(ExperimentalFeature2) {
  ExperimentalFeature2[ExperimentalFeature2["WebFlexBasis"] = 0] = "WebFlexBasis";
  return ExperimentalFeature2;
}({});
var FlexDirection = /* @__PURE__ */ function(FlexDirection2) {
  FlexDirection2[FlexDirection2["Column"] = 0] = "Column";
  FlexDirection2[FlexDirection2["ColumnReverse"] = 1] = "ColumnReverse";
  FlexDirection2[FlexDirection2["Row"] = 2] = "Row";
  FlexDirection2[FlexDirection2["RowReverse"] = 3] = "RowReverse";
  return FlexDirection2;
}({});
var Gutter = /* @__PURE__ */ function(Gutter2) {
  Gutter2[Gutter2["Column"] = 0] = "Column";
  Gutter2[Gutter2["Row"] = 1] = "Row";
  Gutter2[Gutter2["All"] = 2] = "All";
  return Gutter2;
}({});
var Justify = /* @__PURE__ */ function(Justify2) {
  Justify2[Justify2["FlexStart"] = 0] = "FlexStart";
  Justify2[Justify2["Center"] = 1] = "Center";
  Justify2[Justify2["FlexEnd"] = 2] = "FlexEnd";
  Justify2[Justify2["SpaceBetween"] = 3] = "SpaceBetween";
  Justify2[Justify2["SpaceAround"] = 4] = "SpaceAround";
  Justify2[Justify2["SpaceEvenly"] = 5] = "SpaceEvenly";
  return Justify2;
}({});
var LogLevel = /* @__PURE__ */ function(LogLevel2) {
  LogLevel2[LogLevel2["Error"] = 0] = "Error";
  LogLevel2[LogLevel2["Warn"] = 1] = "Warn";
  LogLevel2[LogLevel2["Info"] = 2] = "Info";
  LogLevel2[LogLevel2["Debug"] = 3] = "Debug";
  LogLevel2[LogLevel2["Verbose"] = 4] = "Verbose";
  LogLevel2[LogLevel2["Fatal"] = 5] = "Fatal";
  return LogLevel2;
}({});
var MeasureMode = /* @__PURE__ */ function(MeasureMode2) {
  MeasureMode2[MeasureMode2["Undefined"] = 0] = "Undefined";
  MeasureMode2[MeasureMode2["Exactly"] = 1] = "Exactly";
  MeasureMode2[MeasureMode2["AtMost"] = 2] = "AtMost";
  return MeasureMode2;
}({});
var NodeType = /* @__PURE__ */ function(NodeType2) {
  NodeType2[NodeType2["Default"] = 0] = "Default";
  NodeType2[NodeType2["Text"] = 1] = "Text";
  return NodeType2;
}({});
var Overflow = /* @__PURE__ */ function(Overflow2) {
  Overflow2[Overflow2["Visible"] = 0] = "Visible";
  Overflow2[Overflow2["Hidden"] = 1] = "Hidden";
  Overflow2[Overflow2["Scroll"] = 2] = "Scroll";
  return Overflow2;
}({});
var PositionType = /* @__PURE__ */ function(PositionType2) {
  PositionType2[PositionType2["Static"] = 0] = "Static";
  PositionType2[PositionType2["Relative"] = 1] = "Relative";
  PositionType2[PositionType2["Absolute"] = 2] = "Absolute";
  return PositionType2;
}({});
var Unit = /* @__PURE__ */ function(Unit2) {
  Unit2[Unit2["Undefined"] = 0] = "Undefined";
  Unit2[Unit2["Point"] = 1] = "Point";
  Unit2[Unit2["Percent"] = 2] = "Percent";
  Unit2[Unit2["Auto"] = 3] = "Auto";
  return Unit2;
}({});
var Wrap = /* @__PURE__ */ function(Wrap2) {
  Wrap2[Wrap2["NoWrap"] = 0] = "NoWrap";
  Wrap2[Wrap2["Wrap"] = 1] = "Wrap";
  Wrap2[Wrap2["WrapReverse"] = 2] = "WrapReverse";
  return Wrap2;
}({});
var constants = {
  ALIGN_AUTO: Align.Auto,
  ALIGN_FLEX_START: Align.FlexStart,
  ALIGN_CENTER: Align.Center,
  ALIGN_FLEX_END: Align.FlexEnd,
  ALIGN_STRETCH: Align.Stretch,
  ALIGN_BASELINE: Align.Baseline,
  ALIGN_SPACE_BETWEEN: Align.SpaceBetween,
  ALIGN_SPACE_AROUND: Align.SpaceAround,
  ALIGN_SPACE_EVENLY: Align.SpaceEvenly,
  BOX_SIZING_BORDER_BOX: BoxSizing.BorderBox,
  BOX_SIZING_CONTENT_BOX: BoxSizing.ContentBox,
  DIMENSION_WIDTH: Dimension.Width,
  DIMENSION_HEIGHT: Dimension.Height,
  DIRECTION_INHERIT: Direction.Inherit,
  DIRECTION_LTR: Direction.LTR,
  DIRECTION_RTL: Direction.RTL,
  DISPLAY_FLEX: Display.Flex,
  DISPLAY_NONE: Display.None,
  DISPLAY_CONTENTS: Display.Contents,
  EDGE_LEFT: Edge.Left,
  EDGE_TOP: Edge.Top,
  EDGE_RIGHT: Edge.Right,
  EDGE_BOTTOM: Edge.Bottom,
  EDGE_START: Edge.Start,
  EDGE_END: Edge.End,
  EDGE_HORIZONTAL: Edge.Horizontal,
  EDGE_VERTICAL: Edge.Vertical,
  EDGE_ALL: Edge.All,
  ERRATA_NONE: Errata.None,
  ERRATA_STRETCH_FLEX_BASIS: Errata.StretchFlexBasis,
  ERRATA_ABSOLUTE_POSITION_WITHOUT_INSETS_EXCLUDES_PADDING: Errata.AbsolutePositionWithoutInsetsExcludesPadding,
  ERRATA_ABSOLUTE_PERCENT_AGAINST_INNER_SIZE: Errata.AbsolutePercentAgainstInnerSize,
  ERRATA_ALL: Errata.All,
  ERRATA_CLASSIC: Errata.Classic,
  EXPERIMENTAL_FEATURE_WEB_FLEX_BASIS: ExperimentalFeature.WebFlexBasis,
  FLEX_DIRECTION_COLUMN: FlexDirection.Column,
  FLEX_DIRECTION_COLUMN_REVERSE: FlexDirection.ColumnReverse,
  FLEX_DIRECTION_ROW: FlexDirection.Row,
  FLEX_DIRECTION_ROW_REVERSE: FlexDirection.RowReverse,
  GUTTER_COLUMN: Gutter.Column,
  GUTTER_ROW: Gutter.Row,
  GUTTER_ALL: Gutter.All,
  JUSTIFY_FLEX_START: Justify.FlexStart,
  JUSTIFY_CENTER: Justify.Center,
  JUSTIFY_FLEX_END: Justify.FlexEnd,
  JUSTIFY_SPACE_BETWEEN: Justify.SpaceBetween,
  JUSTIFY_SPACE_AROUND: Justify.SpaceAround,
  JUSTIFY_SPACE_EVENLY: Justify.SpaceEvenly,
  LOG_LEVEL_ERROR: LogLevel.Error,
  LOG_LEVEL_WARN: LogLevel.Warn,
  LOG_LEVEL_INFO: LogLevel.Info,
  LOG_LEVEL_DEBUG: LogLevel.Debug,
  LOG_LEVEL_VERBOSE: LogLevel.Verbose,
  LOG_LEVEL_FATAL: LogLevel.Fatal,
  MEASURE_MODE_UNDEFINED: MeasureMode.Undefined,
  MEASURE_MODE_EXACTLY: MeasureMode.Exactly,
  MEASURE_MODE_AT_MOST: MeasureMode.AtMost,
  NODE_TYPE_DEFAULT: NodeType.Default,
  NODE_TYPE_TEXT: NodeType.Text,
  OVERFLOW_VISIBLE: Overflow.Visible,
  OVERFLOW_HIDDEN: Overflow.Hidden,
  OVERFLOW_SCROLL: Overflow.Scroll,
  POSITION_TYPE_STATIC: PositionType.Static,
  POSITION_TYPE_RELATIVE: PositionType.Relative,
  POSITION_TYPE_ABSOLUTE: PositionType.Absolute,
  UNIT_UNDEFINED: Unit.Undefined,
  UNIT_POINT: Unit.Point,
  UNIT_PERCENT: Unit.Percent,
  UNIT_AUTO: Unit.Auto,
  WRAP_NO_WRAP: Wrap.NoWrap,
  WRAP_WRAP: Wrap.Wrap,
  WRAP_WRAP_REVERSE: Wrap.WrapReverse
};
var YGEnums_default = constants;

// node_modules/yoga-layout/dist/src/wrapAssembly.js
function wrapAssembly(lib) {
  function patch(prototype, name, fn) {
    const original = prototype[name];
    prototype[name] = function() {
      for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
        args[_key] = arguments[_key];
      }
      return fn.call(this, original, ...args);
    };
  }
  for (const fnName of ["setPosition", "setMargin", "setFlexBasis", "setWidth", "setHeight", "setMinWidth", "setMinHeight", "setMaxWidth", "setMaxHeight", "setPadding", "setGap"]) {
    const methods = {
      [Unit.Point]: lib.Node.prototype[fnName],
      [Unit.Percent]: lib.Node.prototype[`${fnName}Percent`],
      [Unit.Auto]: lib.Node.prototype[`${fnName}Auto`]
    };
    patch(lib.Node.prototype, fnName, function(original) {
      for (var _len2 = arguments.length, args = new Array(_len2 > 1 ? _len2 - 1 : 0), _key2 = 1; _key2 < _len2; _key2++) {
        args[_key2 - 1] = arguments[_key2];
      }
      const value = args.pop();
      let unit, asNumber;
      if (value === "auto") {
        unit = Unit.Auto;
        asNumber = void 0;
      } else if (typeof value === "object") {
        unit = value.unit;
        asNumber = value.valueOf();
      } else {
        unit = typeof value === "string" && value.endsWith("%") ? Unit.Percent : Unit.Point;
        asNumber = parseFloat(value);
        if (value !== void 0 && !Number.isNaN(value) && Number.isNaN(asNumber)) {
          throw new Error(`Invalid value ${value} for ${fnName}`);
        }
      }
      if (!methods[unit]) throw new Error(`Failed to execute "${fnName}": Unsupported unit '${value}'`);
      if (asNumber !== void 0) {
        return methods[unit].call(this, ...args, asNumber);
      } else {
        return methods[unit].call(this, ...args);
      }
    });
  }
  function wrapMeasureFunction(measureFunction) {
    return lib.MeasureCallback.implement({
      measure: function() {
        const {
          width,
          height
        } = measureFunction(...arguments);
        return {
          width: width ?? NaN,
          height: height ?? NaN
        };
      }
    });
  }
  patch(lib.Node.prototype, "setMeasureFunc", function(original, measureFunc) {
    if (measureFunc) {
      return original.call(this, wrapMeasureFunction(measureFunc));
    } else {
      return this.unsetMeasureFunc();
    }
  });
  function wrapDirtiedFunc(dirtiedFunction) {
    return lib.DirtiedCallback.implement({
      dirtied: dirtiedFunction
    });
  }
  patch(lib.Node.prototype, "setDirtiedFunc", function(original, dirtiedFunc) {
    original.call(this, wrapDirtiedFunc(dirtiedFunc));
  });
  patch(lib.Config.prototype, "free", function() {
    lib.Config.destroy(this);
  });
  patch(lib.Node, "create", (_, config) => {
    return config ? lib.Node.createWithConfig(config) : lib.Node.createDefault();
  });
  patch(lib.Node.prototype, "free", function() {
    lib.Node.destroy(this);
  });
  patch(lib.Node.prototype, "freeRecursive", function() {
    for (let t = 0, T = this.getChildCount(); t < T; ++t) {
      this.getChild(0).freeRecursive();
    }
    this.free();
  });
  patch(lib.Node.prototype, "calculateLayout", function(original) {
    let width = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : NaN;
    let height = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : NaN;
    let direction = arguments.length > 3 && arguments[3] !== void 0 ? arguments[3] : Direction.LTR;
    return original.call(this, width, height, direction);
  });
  return {
    Config: lib.Config,
    Node: lib.Node,
    ...YGEnums_default
  };
}

// node_modules/yoga-layout/dist/src/index.js
var Yoga = wrapAssembly(await yoga_wasm_base64_esm_default());

// node_modules/ink/build/measure-element.js
function calculateScrollbarThumb(options) {
  const { scrollbarDimension, clientDimension, scrollDimension, scrollPosition, axis } = options;
  const scrollbarDimensionHalves = scrollbarDimension * 2;
  const thumbDimensionHalves = Math.max(axis === "vertical" ? 2 : 1, Math.round(clientDimension / scrollDimension * scrollbarDimensionHalves));
  const maxScrollPosition = scrollDimension - clientDimension;
  const maxThumbPosition = scrollbarDimensionHalves - thumbDimensionHalves;
  const thumbPosition = maxScrollPosition > 0 ? Math.round(scrollPosition / maxScrollPosition * maxThumbPosition) : 0;
  const thumbStartHalf = thumbPosition;
  const thumbEndHalf = thumbPosition + thumbDimensionHalves;
  const startIndex = Math.floor(thumbStartHalf / 2);
  const endIndex = Math.min(scrollbarDimension, Math.ceil(thumbEndHalf / 2));
  return { startIndex, endIndex, thumbStartHalf, thumbEndHalf };
}

// node_modules/ink/node_modules/chalk/source/vendor/ansi-styles/index.js
var ANSI_BACKGROUND_OFFSET2 = 10;
var wrapAnsi162 = (offset = 0) => (code) => `\x1B[${code + offset}m`;
var wrapAnsi2562 = (offset = 0) => (code) => `\x1B[${38 + offset};5;${code}m`;
var wrapAnsi16m2 = (offset = 0) => (red, green, blue) => `\x1B[${38 + offset};2;${red};${green};${blue}m`;
var styles2 = {
  modifier: {
    reset: [0, 0],
    // 21 isn't widely supported and 22 does the same thing
    bold: [1, 22],
    dim: [2, 22],
    italic: [3, 23],
    underline: [4, 24],
    overline: [53, 55],
    inverse: [7, 27],
    hidden: [8, 28],
    strikethrough: [9, 29]
  },
  color: {
    black: [30, 39],
    red: [31, 39],
    green: [32, 39],
    yellow: [33, 39],
    blue: [34, 39],
    magenta: [35, 39],
    cyan: [36, 39],
    white: [37, 39],
    // Bright color
    blackBright: [90, 39],
    gray: [90, 39],
    // Alias of `blackBright`
    grey: [90, 39],
    // Alias of `blackBright`
    redBright: [91, 39],
    greenBright: [92, 39],
    yellowBright: [93, 39],
    blueBright: [94, 39],
    magentaBright: [95, 39],
    cyanBright: [96, 39],
    whiteBright: [97, 39]
  },
  bgColor: {
    bgBlack: [40, 49],
    bgRed: [41, 49],
    bgGreen: [42, 49],
    bgYellow: [43, 49],
    bgBlue: [44, 49],
    bgMagenta: [45, 49],
    bgCyan: [46, 49],
    bgWhite: [47, 49],
    // Bright color
    bgBlackBright: [100, 49],
    bgGray: [100, 49],
    // Alias of `bgBlackBright`
    bgGrey: [100, 49],
    // Alias of `bgBlackBright`
    bgRedBright: [101, 49],
    bgGreenBright: [102, 49],
    bgYellowBright: [103, 49],
    bgBlueBright: [104, 49],
    bgMagentaBright: [105, 49],
    bgCyanBright: [106, 49],
    bgWhiteBright: [107, 49]
  }
};
var modifierNames2 = Object.keys(styles2.modifier);
var foregroundColorNames2 = Object.keys(styles2.color);
var backgroundColorNames2 = Object.keys(styles2.bgColor);
var colorNames2 = [...foregroundColorNames2, ...backgroundColorNames2];
function assembleStyles2() {
  const codes = /* @__PURE__ */ new Map();
  for (const [groupName, group] of Object.entries(styles2)) {
    for (const [styleName, style] of Object.entries(group)) {
      styles2[styleName] = {
        open: `\x1B[${style[0]}m`,
        close: `\x1B[${style[1]}m`
      };
      group[styleName] = styles2[styleName];
      codes.set(style[0], style[1]);
    }
    Object.defineProperty(styles2, groupName, {
      value: group,
      enumerable: false
    });
  }
  Object.defineProperty(styles2, "codes", {
    value: codes,
    enumerable: false
  });
  styles2.color.close = "\x1B[39m";
  styles2.bgColor.close = "\x1B[49m";
  styles2.color.ansi = wrapAnsi162();
  styles2.color.ansi256 = wrapAnsi2562();
  styles2.color.ansi16m = wrapAnsi16m2();
  styles2.bgColor.ansi = wrapAnsi162(ANSI_BACKGROUND_OFFSET2);
  styles2.bgColor.ansi256 = wrapAnsi2562(ANSI_BACKGROUND_OFFSET2);
  styles2.bgColor.ansi16m = wrapAnsi16m2(ANSI_BACKGROUND_OFFSET2);
  Object.defineProperties(styles2, {
    rgbToAnsi256: {
      value(red, green, blue) {
        if (red === green && green === blue) {
          if (red < 8) {
            return 16;
          }
          if (red > 248) {
            return 231;
          }
          return Math.round((red - 8) / 247 * 24) + 232;
        }
        return 16 + 36 * Math.round(red / 255 * 5) + 6 * Math.round(green / 255 * 5) + Math.round(blue / 255 * 5);
      },
      enumerable: false
    },
    hexToRgb: {
      value(hex) {
        const matches = /[a-f\d]{6}|[a-f\d]{3}/i.exec(hex.toString(16));
        if (!matches) {
          return [0, 0, 0];
        }
        let [colorString] = matches;
        if (colorString.length === 3) {
          colorString = [...colorString].map((character) => character + character).join("");
        }
        const integer = Number.parseInt(colorString, 16);
        return [
          /* eslint-disable no-bitwise */
          integer >> 16 & 255,
          integer >> 8 & 255,
          integer & 255
          /* eslint-enable no-bitwise */
        ];
      },
      enumerable: false
    },
    hexToAnsi256: {
      value: (hex) => styles2.rgbToAnsi256(...styles2.hexToRgb(hex)),
      enumerable: false
    },
    ansi256ToAnsi: {
      value(code) {
        if (code < 8) {
          return 30 + code;
        }
        if (code < 16) {
          return 90 + (code - 8);
        }
        let red;
        let green;
        let blue;
        if (code >= 232) {
          red = ((code - 232) * 10 + 8) / 255;
          green = red;
          blue = red;
        } else {
          code -= 16;
          const remainder = code % 36;
          red = Math.floor(code / 36) / 5;
          green = Math.floor(remainder / 6) / 5;
          blue = remainder % 6 / 5;
        }
        const value = Math.max(red, green, blue) * 2;
        if (value === 0) {
          return 30;
        }
        let result = 30 + (Math.round(blue) << 2 | Math.round(green) << 1 | Math.round(red));
        if (value === 2) {
          result += 60;
        }
        return result;
      },
      enumerable: false
    },
    rgbToAnsi: {
      value: (red, green, blue) => styles2.ansi256ToAnsi(styles2.rgbToAnsi256(red, green, blue)),
      enumerable: false
    },
    hexToAnsi: {
      value: (hex) => styles2.ansi256ToAnsi(styles2.hexToAnsi256(hex)),
      enumerable: false
    }
  });
  return styles2;
}
var ansiStyles2 = assembleStyles2();
var ansi_styles_default2 = ansiStyles2;

// node_modules/ink/node_modules/chalk/source/vendor/supports-color/index.js
import process3 from "node:process";
import os from "node:os";
import tty from "node:tty";
function hasFlag(flag, argv = globalThis.Deno ? globalThis.Deno.args : process3.argv) {
  const prefix = flag.startsWith("-") ? "" : flag.length === 1 ? "-" : "--";
  const position = argv.indexOf(prefix + flag);
  const terminatorPosition = argv.indexOf("--");
  return position !== -1 && (terminatorPosition === -1 || position < terminatorPosition);
}
var { env } = process3;
var flagForceColor;
if (hasFlag("no-color") || hasFlag("no-colors") || hasFlag("color=false") || hasFlag("color=never")) {
  flagForceColor = 0;
} else if (hasFlag("color") || hasFlag("colors") || hasFlag("color=true") || hasFlag("color=always")) {
  flagForceColor = 1;
}
function envForceColor() {
  if ("FORCE_COLOR" in env) {
    if (env.FORCE_COLOR === "true") {
      return 1;
    }
    if (env.FORCE_COLOR === "false") {
      return 0;
    }
    return env.FORCE_COLOR.length === 0 ? 1 : Math.min(Number.parseInt(env.FORCE_COLOR, 10), 3);
  }
}
function translateLevel(level) {
  if (level === 0) {
    return false;
  }
  return {
    level,
    hasBasic: true,
    has256: level >= 2,
    has16m: level >= 3
  };
}
function _supportsColor(haveStream, { streamIsTTY, sniffFlags = true } = {}) {
  const noFlagForceColor = envForceColor();
  if (noFlagForceColor !== void 0) {
    flagForceColor = noFlagForceColor;
  }
  const forceColor = sniffFlags ? flagForceColor : noFlagForceColor;
  if (forceColor === 0) {
    return 0;
  }
  if (sniffFlags) {
    if (hasFlag("color=16m") || hasFlag("color=full") || hasFlag("color=truecolor")) {
      return 3;
    }
    if (hasFlag("color=256")) {
      return 2;
    }
  }
  if ("TF_BUILD" in env && "AGENT_NAME" in env) {
    return 1;
  }
  if (haveStream && !streamIsTTY && forceColor === void 0) {
    return 0;
  }
  const min = forceColor || 0;
  if (env.TERM === "dumb") {
    return min;
  }
  if (process3.platform === "win32") {
    const osRelease = os.release().split(".");
    if (Number(osRelease[0]) >= 10 && Number(osRelease[2]) >= 10586) {
      return Number(osRelease[2]) >= 14931 ? 3 : 2;
    }
    return 1;
  }
  if ("CI" in env) {
    if (["GITHUB_ACTIONS", "GITEA_ACTIONS", "CIRCLECI"].some((key) => key in env)) {
      return 3;
    }
    if (["TRAVIS", "APPVEYOR", "GITLAB_CI", "BUILDKITE", "DRONE"].some((sign) => sign in env) || env.CI_NAME === "codeship") {
      return 1;
    }
    return min;
  }
  if ("TEAMCITY_VERSION" in env) {
    return /^(9\.(0*[1-9]\d*)\.|\d{2,}\.)/.test(env.TEAMCITY_VERSION) ? 1 : 0;
  }
  if (env.COLORTERM === "truecolor") {
    return 3;
  }
  if (env.TERM === "xterm-kitty") {
    return 3;
  }
  if (env.TERM === "xterm-ghostty") {
    return 3;
  }
  if (env.TERM === "wezterm") {
    return 3;
  }
  if ("TERM_PROGRAM" in env) {
    const version = Number.parseInt((env.TERM_PROGRAM_VERSION || "").split(".")[0], 10);
    switch (env.TERM_PROGRAM) {
      case "iTerm.app": {
        return version >= 3 ? 3 : 2;
      }
      case "Apple_Terminal": {
        return 2;
      }
    }
  }
  if (/-256(color)?$/i.test(env.TERM)) {
    return 2;
  }
  if (/^screen|^xterm|^vt100|^vt220|^rxvt|color|ansi|cygwin|linux/i.test(env.TERM)) {
    return 1;
  }
  if ("COLORTERM" in env) {
    return 1;
  }
  return min;
}
function createSupportsColor(stream, options = {}) {
  const level = _supportsColor(stream, {
    streamIsTTY: stream && stream.isTTY,
    ...options
  });
  return translateLevel(level);
}
var supportsColor = {
  stdout: createSupportsColor({ isTTY: tty.isatty(1) }),
  stderr: createSupportsColor({ isTTY: tty.isatty(2) })
};
var supports_color_default = supportsColor;

// node_modules/ink/node_modules/chalk/source/utilities.js
function stringReplaceAll(string, substring, replacer) {
  let index = string.indexOf(substring);
  if (index === -1) {
    return string;
  }
  const substringLength = substring.length;
  let endIndex = 0;
  let returnValue = "";
  do {
    returnValue += string.slice(endIndex, index) + substring + replacer;
    endIndex = index + substringLength;
    index = string.indexOf(substring, endIndex);
  } while (index !== -1);
  returnValue += string.slice(endIndex);
  return returnValue;
}
function stringEncaseCRLFWithFirstIndex(string, prefix, postfix, index) {
  let endIndex = 0;
  let returnValue = "";
  do {
    const gotCR = string[index - 1] === "\r";
    returnValue += string.slice(endIndex, gotCR ? index - 1 : index) + prefix + (gotCR ? "\r\n" : "\n") + postfix;
    endIndex = index + 1;
    index = string.indexOf("\n", endIndex);
  } while (index !== -1);
  returnValue += string.slice(endIndex);
  return returnValue;
}

// node_modules/ink/node_modules/chalk/source/index.js
var { stdout: stdoutColor, stderr: stderrColor } = supports_color_default;
var GENERATOR = Symbol("GENERATOR");
var STYLER = Symbol("STYLER");
var IS_EMPTY = Symbol("IS_EMPTY");
var levelMapping = [
  "ansi",
  "ansi",
  "ansi256",
  "ansi16m"
];
var styles3 = /* @__PURE__ */ Object.create(null);
var applyOptions = (object, options = {}) => {
  if (options.level && !(Number.isInteger(options.level) && options.level >= 0 && options.level <= 3)) {
    throw new Error("The `level` option should be an integer from 0 to 3");
  }
  const colorLevel = stdoutColor ? stdoutColor.level : 0;
  object.level = options.level === void 0 ? colorLevel : options.level;
};
var chalkFactory = (options) => {
  const chalk2 = (...strings) => strings.join(" ");
  applyOptions(chalk2, options);
  Object.setPrototypeOf(chalk2, createChalk.prototype);
  return chalk2;
};
function createChalk(options) {
  return chalkFactory(options);
}
Object.setPrototypeOf(createChalk.prototype, Function.prototype);
for (const [styleName, style] of Object.entries(ansi_styles_default2)) {
  styles3[styleName] = {
    get() {
      const builder = createBuilder(this, createStyler(style.open, style.close, this[STYLER]), this[IS_EMPTY]);
      Object.defineProperty(this, styleName, { value: builder });
      return builder;
    }
  };
}
styles3.visible = {
  get() {
    const builder = createBuilder(this, this[STYLER], true);
    Object.defineProperty(this, "visible", { value: builder });
    return builder;
  }
};
var getModelAnsi = (model, level, type, ...arguments_) => {
  if (model === "rgb") {
    if (level === "ansi16m") {
      return ansi_styles_default2[type].ansi16m(...arguments_);
    }
    if (level === "ansi256") {
      return ansi_styles_default2[type].ansi256(ansi_styles_default2.rgbToAnsi256(...arguments_));
    }
    return ansi_styles_default2[type].ansi(ansi_styles_default2.rgbToAnsi(...arguments_));
  }
  if (model === "hex") {
    return getModelAnsi("rgb", level, type, ...ansi_styles_default2.hexToRgb(...arguments_));
  }
  return ansi_styles_default2[type][model](...arguments_);
};
var usedModels = ["rgb", "hex", "ansi256"];
for (const model of usedModels) {
  styles3[model] = {
    get() {
      const { level } = this;
      return function(...arguments_) {
        const styler = createStyler(getModelAnsi(model, levelMapping[level], "color", ...arguments_), ansi_styles_default2.color.close, this[STYLER]);
        return createBuilder(this, styler, this[IS_EMPTY]);
      };
    }
  };
  const bgModel = "bg" + model[0].toUpperCase() + model.slice(1);
  styles3[bgModel] = {
    get() {
      const { level } = this;
      return function(...arguments_) {
        const styler = createStyler(getModelAnsi(model, levelMapping[level], "bgColor", ...arguments_), ansi_styles_default2.bgColor.close, this[STYLER]);
        return createBuilder(this, styler, this[IS_EMPTY]);
      };
    }
  };
}
var proto = Object.defineProperties(() => {
}, {
  ...styles3,
  level: {
    enumerable: true,
    get() {
      return this[GENERATOR].level;
    },
    set(level) {
      this[GENERATOR].level = level;
    }
  }
});
var createStyler = (open, close, parent) => {
  let openAll;
  let closeAll;
  if (parent === void 0) {
    openAll = open;
    closeAll = close;
  } else {
    openAll = parent.openAll + open;
    closeAll = close + parent.closeAll;
  }
  return {
    open,
    close,
    openAll,
    closeAll,
    parent
  };
};
var createBuilder = (self, _styler, _isEmpty) => {
  const builder = (...arguments_) => applyStyle(builder, arguments_.length === 1 ? "" + arguments_[0] : arguments_.join(" "));
  Object.setPrototypeOf(builder, proto);
  builder[GENERATOR] = self;
  builder[STYLER] = _styler;
  builder[IS_EMPTY] = _isEmpty;
  return builder;
};
var applyStyle = (self, string) => {
  if (self.level <= 0 || !string) {
    return self[IS_EMPTY] ? "" : string;
  }
  let styler = self[STYLER];
  if (styler === void 0) {
    return string;
  }
  const { openAll, closeAll } = styler;
  if (string.includes("\x1B")) {
    while (styler !== void 0) {
      string = stringReplaceAll(string, styler.close, styler.open);
      styler = styler.parent;
    }
  }
  const lfIndex = string.indexOf("\n");
  if (lfIndex !== -1) {
    string = stringEncaseCRLFWithFirstIndex(string, closeAll, openAll, lfIndex);
  }
  return openAll + string + closeAll;
};
Object.defineProperties(createChalk.prototype, styles3);
var chalk = createChalk();
var chalkStderr = createChalk({ level: stderrColor ? stderrColor.level : 0 });
var source_default = chalk;

// node_modules/ink/build/colorize.js
var rgbRegex = /^rgb\(\s?(\d+),\s?(\d+),\s?(\d+)\s?\)$/;
var ansiRegex = /^ansi256\(\s?(\d+)\s?\)$/;
var isNamedColor = (color) => {
  return color in source_default;
};
var colorize = (str, color, type) => {
  if (!color) {
    return str;
  }
  if (isNamedColor(color)) {
    if (type === "foreground") {
      return source_default[color](str);
    }
    const methodName = `bg${color[0].toUpperCase() + color.slice(1)}`;
    return source_default[methodName](str);
  }
  if (color.startsWith("#")) {
    return type === "foreground" ? source_default.hex(color)(str) : source_default.bgHex(color)(str);
  }
  if (color.startsWith("ansi256")) {
    const matches = ansiRegex.exec(color);
    if (!matches) {
      return str;
    }
    const value = Number(matches[1]);
    return type === "foreground" ? source_default.ansi256(value)(str) : source_default.bgAnsi256(value)(str);
  }
  if (color.startsWith("rgb")) {
    const matches = rgbRegex.exec(color);
    if (!matches) {
      return str;
    }
    const firstValue = Number(matches[1]);
    const secondValue = Number(matches[2]);
    const thirdValue = Number(matches[3]);
    return type === "foreground" ? source_default.rgb(firstValue, secondValue, thirdValue)(str) : source_default.bgRgb(firstValue, secondValue, thirdValue)(str);
  }
  return str;
};
var getBackgroundColorEscape = (color) => {
  const colorized = colorize("x", color, "background");
  if (colorized !== "x") {
    return colorized.split("x")[0];
  }
  return void 0;
};
var colorize_default = colorize;

// node_modules/ink/build/render-scrollbar.js
var renderScrollbar = ({ layout, clip, axis, color, setChar, getExistingChar }) => {
  const { x, y, thumb: { start: startIndex, end: endIndex, startHalf: thumbStartHalf, endHalf: thumbEndHalf } } = layout;
  if (axis === "vertical") {
    for (let i = startIndex; i < endIndex; i++) {
      const drawY = y + i;
      const drawX = x;
      if (drawY >= clip.y && drawY < clip.y + clip.h && drawX >= clip.x && drawX < clip.x + clip.w) {
        let char = "\u2588";
        const hasUpper = 2 * i >= thumbStartHalf && 2 * i < thumbEndHalf;
        const hasLower = 2 * i + 1 >= thumbStartHalf && 2 * i + 1 < thumbEndHalf;
        if (hasUpper && !hasLower) {
          char = "\u2580";
        } else if (!hasUpper && hasLower) {
          char = "\u2584";
        }
        const charString = color ? colorize_default(char, color, "foreground") : char;
        const styled = toStyledCharacters(charString);
        if (styled.length > 0) {
          let bgColor = styled.getBgColor(0);
          if (getExistingChar && (char === "\u2580" || char === "\u2584")) {
            const existing = getExistingChar(drawX, drawY);
            if (existing?.bgColor) {
              bgColor = existing.bgColor;
            }
          }
          setChar(drawX, drawY, styled.getValue(0), styled.getFormatFlags(0), styled.getFgColor(0), bgColor, styled.getLink(0));
        }
      }
    }
  } else {
    for (let i = startIndex; i < endIndex; i++) {
      const drawX = x + i;
      const drawY = y;
      if (drawY >= clip.y && drawY < clip.y + clip.h && drawX >= clip.x && drawX < clip.x + clip.w) {
        let char = "\u2588";
        const hasLeft = 2 * i >= thumbStartHalf && 2 * i < thumbEndHalf;
        const hasRight = 2 * i + 1 >= thumbStartHalf && 2 * i + 1 < thumbEndHalf;
        if (hasLeft && !hasRight) {
          char = "\u258C";
        } else if (!hasLeft && hasRight) {
          char = "\u2590";
        }
        const charString = color ? colorize_default(char, color, "foreground") : char;
        const styled = toStyledCharacters(charString);
        if (styled.length > 0) {
          let bgColor = styled.getBgColor(0);
          if (getExistingChar && (char === "\u258C" || char === "\u2590")) {
            const existing = getExistingChar(drawX, drawY);
            if (existing?.bgColor) {
              bgColor = existing.bgColor;
            }
          }
          setChar(drawX, drawY, styled.getValue(0), styled.getFormatFlags(0), styled.getFgColor(0), bgColor, styled.getLink(0));
        }
      }
    }
  }
};

// node_modules/ink/build/output.js
function treesEqual(a, b) {
  if (a === b)
    return true;
  if (a.id !== b.id)
    return false;
  if (a.children.length !== b.children.length)
    return false;
  for (let i = 0; i < a.children.length; i++) {
    if (!treesEqual(a.children[i], b.children[i]))
      return false;
  }
  return true;
}
var regionLayoutProperties = [
  "x",
  "y",
  "width",
  "height",
  "scrollTop",
  "scrollLeft",
  "scrollHeight",
  "scrollWidth",
  "isScrollable",
  "isVerticallyScrollable",
  "isHorizontallyScrollable",
  "scrollbarVisible",
  "overflowToBackbuffer",
  "marginRight",
  "marginBottom",
  "scrollbarThumbColor",
  "backgroundColor",
  "opaque",
  "borderTop",
  "borderBottom"
];
function copyRegionProperty(target, source, key) {
  const value = source[key];
  if (value !== void 0) {
    target[key] = value;
  }
}

// node_modules/ink/build/serialization.js
import { Buffer as Buffer2 } from "node:buffer";
var hasStylesMask = 2;
var fullWidthMask = 1;
var isRepeatedCharMask = 4;
var isAsciiMixedMask = 8;
var Serializer = class {
  // eslint-disable-next-line @typescript-eslint/ban-types
  buffer;
  currentSize = 0;
  constructor(initialSize = 1024 * 1024) {
    this.buffer = Buffer2.allocUnsafe(initialSize);
  }
  serialize(lines) {
    this.currentSize = 0;
    this.writeUint32(lines.length);
    for (const line of lines) {
      this.writeLine(line);
    }
    const result = Buffer2.allocUnsafe(this.currentSize);
    this.buffer.copy(result, 0, 0, this.currentSize);
    return result;
  }
  ensureCapacity(size) {
    if (this.currentSize + size > this.buffer.length) {
      const newSize = Math.max(this.buffer.length * 2, this.currentSize + size + 1024 * 1024);
      const newBuffer = Buffer2.allocUnsafe(newSize);
      this.buffer.copy(newBuffer, 0, 0, this.currentSize);
      this.buffer = newBuffer;
    }
  }
  writeLine(line) {
    if (line.length === 0) {
      this.writeUint32(0);
      return;
    }
    const spans = line.getSpans();
    this.writeUint32(spans.length);
    let offset = 0;
    for (const span of spans) {
      this.writeSpan(line, span, offset);
      offset += span.length;
    }
  }
  writeSpan(line, span, start) {
    this.writeUint32(span.length);
    const end = start + span.length;
    const firstVal = line.getValue(start);
    const firstFullWidth = line.getFullWidth(start);
    let isRepeatedChar = true;
    let isAsciiMixed = true;
    for (let i = start; i < end; i++) {
      const val = line.getValue(i);
      if (val !== firstVal || line.getFullWidth(i) !== firstFullWidth) {
        isRepeatedChar = false;
      }
      if (line.getFullWidth(i) || val.length !== 1) {
        isAsciiMixed = false;
      }
    }
    let flags = 0;
    const hasStyles = (span.formatFlags & ~FULL_WIDTH_MASK) !== 0 || span.fgColor || span.bgColor || span.link;
    if (hasStyles) {
      flags |= hasStylesMask;
    }
    if (isRepeatedChar) {
      flags |= isRepeatedCharMask;
    } else if (isAsciiMixed) {
      flags |= isAsciiMixedMask;
    }
    this.writeUint8(flags);
    if (hasStyles) {
      this.writeUint8(span.formatFlags);
      this.writeString(span.fgColor || "");
      this.writeString(span.bgColor || "");
      this.writeString(span.link || "");
    }
    if (isRepeatedChar) {
      let charFlags = 0;
      if (firstFullWidth) {
        charFlags |= fullWidthMask;
      }
      this.writeUint8(charFlags);
      this.writeString(firstVal || "");
    } else if (isAsciiMixed) {
      let concat = "";
      for (let i = start; i < end; i++) {
        concat += line.getValue(i);
      }
      this.writeString(concat);
    } else {
      for (let i = start; i < end; i++) {
        let charFlags = 0;
        if (line.getFullWidth(i)) {
          charFlags |= fullWidthMask;
        }
        this.writeUint8(charFlags);
        this.writeString(line.getValue(i) || "");
      }
    }
  }
  writeString(str) {
    const len = Buffer2.byteLength(str);
    this.ensureCapacity(2 + len);
    this.buffer.writeUint16LE(len, this.currentSize);
    this.currentSize += 2;
    this.buffer.write(str, this.currentSize, len, "utf8");
    this.currentSize += len;
  }
  writeUint32(value) {
    this.ensureCapacity(4);
    this.buffer.writeUint32LE(value, this.currentSize);
    this.currentSize += 4;
  }
  writeUint8(value) {
    this.ensureCapacity(1);
    this.buffer.writeUint8(value, this.currentSize);
    this.currentSize += 1;
  }
};
var Deserializer = class {
  offset = 0;
  // eslint-disable-next-line @typescript-eslint/ban-types
  buf;
  constructor(buffer2) {
    this.buf = Buffer2.isBuffer(buffer2) ? buffer2 : Buffer2.from(buffer2.buffer, buffer2.byteOffset, buffer2.byteLength);
  }
  deserialize() {
    const lineCount = this.readUint32();
    const lines = [];
    for (let i = 0; i < lineCount; i++) {
      lines.push(this.readLine());
    }
    return lines;
  }
  readLine() {
    const spanCount = this.readUint32();
    const line = new StyledLine();
    for (let i = 0; i < spanCount; i++) {
      this.readSpan(line);
    }
    return line;
  }
  readSpan(line) {
    const spanLength = this.readUint32();
    const flags = this.readUint8();
    const hasStyles = (flags & hasStylesMask) !== 0;
    const isRepeatedChar = (flags & isRepeatedCharMask) !== 0;
    const isAsciiMixed = (flags & isAsciiMixedMask) !== 0;
    let formatFlags = 0;
    let fgColor;
    let bgColor;
    let link2;
    if (hasStyles) {
      formatFlags = this.readUint8();
      fgColor = this.readString() || void 0;
      bgColor = this.readString() || void 0;
      link2 = this.readString() || void 0;
    }
    if (isRepeatedChar) {
      const charFlags = this.readUint8();
      const fullWidth = (charFlags & fullWidthMask) !== 0;
      const value = this.readString();
      let ff = formatFlags;
      if (fullWidth)
        ff |= FULL_WIDTH_MASK;
      for (let i = 0; i < spanLength; i++) {
        line.pushChar(value, ff, fgColor, bgColor, link2);
      }
    } else if (isAsciiMixed) {
      const value = this.readString();
      for (let i = 0; i < spanLength; i++) {
        line.pushChar(value[i], formatFlags, fgColor, bgColor, link2);
      }
    } else {
      for (let i = 0; i < spanLength; i++) {
        const charFlags = this.readUint8();
        const fullWidth = (charFlags & fullWidthMask) !== 0;
        const value = this.readString();
        let ff = formatFlags;
        if (fullWidth)
          ff |= FULL_WIDTH_MASK;
        else
          ff &= ~FULL_WIDTH_MASK;
        line.pushChar(value, ff, fgColor, bgColor, link2);
      }
    }
  }
  readString() {
    const len = this.readUint16();
    const str = this.buf.toString("utf8", this.offset, this.offset + len);
    this.offset += len;
    return str;
  }
  readUint32() {
    const value = this.buf.readUint32LE(this.offset);
    this.offset += 4;
    return value;
  }
  readUint16() {
    const value = this.buf.readUint16LE(this.offset);
    this.offset += 2;
    return value;
  }
  readUint8() {
    const value = this.buf.readUint8(this.offset);
    this.offset += 1;
    return value;
  }
};

// node_modules/ink/build/replay.js
import fs2 from "node:fs";
import { Buffer as Buffer3 } from "node:buffer";
function serializeReplayUpdate(update) {
  const { lines, stickyHeaders, ...rest } = update;
  const result = {
    ...rest
  };
  if (lines) {
    result.lines = {
      totalLength: lines.totalLength,
      updates: lines.updates.map((u) => ({
        start: u.start,
        end: u.end,
        data: Buffer3.from(u.data).toString("base64"),
        source: u.source ? Buffer3.from(u.source).toString("base64") : void 0
      }))
    };
  }
  if (stickyHeaders) {
    result.stickyHeaders = stickyHeaders.map((h) => ({
      ...h,
      lines: Buffer3.from(h.lines).toString("base64"),
      stuckLines: h.stuckLines ? Buffer3.from(h.stuckLines).toString("base64") : void 0,
      styledOutput: Buffer3.from(h.styledOutput).toString("base64")
    }));
  }
  return result;
}
function saveReplay(data, filename) {
  fs2.writeFileSync(filename, JSON.stringify(data, null, 2));
}
function createHumanReadableDump(data) {
  const dumpData = {
    type: data.type,
    columns: data.columns,
    rows: data.rows,
    frames: data.frames.map((frame) => ({
      tree: frame.tree,
      cursorPosition: frame.cursorPosition,
      updates: frame.updates.map((update) => {
        const dumpUpdate = { ...update };
        dumpUpdate["overflowToBackbuffer"] = update.overflowToBackbuffer;
        dumpUpdate["isScrollable"] = update.isScrollable;
        if (update.lines) {
          dumpUpdate["lines"] = {
            totalLength: update.lines.totalLength,
            updates: update.lines.updates.map((u) => {
              const deserializer = new Deserializer(Buffer3.from(u.data));
              const lines = deserializer.deserialize();
              return {
                start: u.start,
                end: u.end,
                text: lines.map((line) => line.getText().trimEnd())
              };
            })
          };
        }
        if (update.stickyHeaders) {
          dumpUpdate["stickyHeaders"] = update.stickyHeaders.map((h) => ({
            ...h,
            lines: new Deserializer(Buffer3.from(h.lines)).deserialize().map((line) => line.getText().trimEnd()),
            stuckLines: h.stuckLines ? new Deserializer(Buffer3.from(h.stuckLines)).deserialize().map((line) => line.getText().trimEnd()) : void 0,
            styledOutput: new Deserializer(Buffer3.from(h.styledOutput)).deserialize().map((line) => line.getText().trimEnd()),
            node: void 0
          }));
        }
        return dumpUpdate;
      })
    }))
  };
  return JSON.stringify(dumpData, null, 2);
}

// node_modules/ink/build/worker/terminal-writer.js
import process5 from "node:process";

// node_modules/ink/build/worker/ansi-utils.js
var enterSynchronizedOutput = "\x1B[?2026h";
var exitSynchronizedOutput = "\x1B[?2026l";
var resetScrollRegion = "\x1B[r";
var ris = "\x1Bc";
var clearScrollbackStandard = "\x1B[3J";
var homeEraseDown = "\x1B[H\x1B[J";
var getMoveCursorDownCode = (skippedLines) => {
  if (skippedLines > 0) {
    if (skippedLines === 1) {
      return base_exports.cursorNextLine;
    }
    return base_exports.cursorDown(skippedLines);
  }
  return "";
};
var getMoveCursorUpCode = (skippedLines) => {
  if (skippedLines > 0) {
    if (skippedLines === 1) {
      return base_exports.cursorPrevLine;
    }
    return base_exports.cursorUp(skippedLines);
  }
  return "";
};
var getDeleteLinesCode = (count) => {
  return `\x1B[${count}M`;
};
var getInsertLinesCode = (count) => {
  return `\x1B[${count}L`;
};
var getSetScrollRegionCode = (top, bottom) => {
  return `\x1B[${top + 1};${bottom}r`;
};

// node_modules/ink/build/worker/platform.js
import process4 from "node:process";
var platform2 = {
  /**
   * Terminal.app doesn't respect scroll regions starting at line 0 for scroll
   * escape sequences. We need to use a workaround for this terminal.
   */
  isAppleTerminal() {
    return process4.env["TERM_PROGRAM"] === "Apple_Terminal";
  }
};

// node_modules/ink/build/worker/terminal-writer.js
var synchronizeOutput = true;
var rainbowColors = [
  "ansi256(17)",
  "ansi256(18)",
  "ansi256(19)",
  "ansi256(20)",
  "ansi256(21)",
  "ansi256(25)",
  "ansi256(26)",
  "ansi256(27)",
  "ansi256(31)",
  "ansi256(32)",
  "ansi256(33)",
  "ansi256(39)",
  "ansi256(63)",
  "ansi256(69)",
  "ansi256(75)"
];
function linesEqual(lineA, lineB) {
  if (lineA === lineB)
    return true;
  if (!lineA || !lineB)
    return false;
  return lineA.equals(lineB);
}
var TerminalWriter = class {
  columns;
  rows;
  stdout;
  isTainted = false;
  debugRainbowColor;
  backbufferDirty = false;
  backbufferScrolledIncorrectly = false;
  backbufferDirtyCurrentFrame = false;
  fullRenderTimeout;
  maxScrollbackLength = 1e3;
  forceScrollToBottomOnBackbufferRefresh = false;
  linesUpdated = 0;
  screen = [];
  backbuffer = [];
  cursorX = -1;
  cursorY = -1;
  targetCursorX = -1;
  targetCursorY = -1;
  scrollRegionTop = -1;
  scrollRegionBottom = -1;
  firstRender = true;
  enableSynchronizedOutput = synchronizeOutput;
  cancelSlowFlush;
  isDone = false;
  outputBuffer = [];
  currentChunkBuffer = [];
  constructor(columns, rows, stdout) {
    this.columns = columns;
    this.rows = rows;
    this.stdout = stdout;
  }
  getLinesUpdated() {
    return this.linesUpdated;
  }
  resetLinesUpdated() {
    this.linesUpdated = 0;
  }
  unkownCursorLocation() {
    this.cursorX = -1;
    this.cursorY = -1;
  }
  writeRaw(text) {
    this.writeHelper(text);
  }
  taintScreen() {
    for (const line of this.screen) {
      if (line) {
        line.tainted = true;
      }
    }
  }
  getBackbufferLength() {
    return this.backbuffer.length;
  }
  getBackbufferEntry(index) {
    return this.backbuffer[index];
  }
  getScreenLine(y) {
    return this.screen[y];
  }
  setBackbuffer(lines) {
    this.backbuffer = lines;
  }
  get isFirstRender() {
    return this.firstRender;
  }
  appendLinesBackbuffer(lines) {
    this.startSynchronizedOutput();
    try {
      for (const line of lines) {
        this.syncLine(line, 0);
        this.applyScrollUpBackbuffer(0, this.rows);
      }
    } finally {
      this.endSynchronizedOutput();
    }
  }
  updateBackbuffer(start, deleteCount, newLines) {
    const backbufferLength = this.backbuffer.length;
    const screenStart = Math.max(0, backbufferLength - this.rows);
    if (start === backbufferLength && deleteCount === 0) {
      this.appendLinesBackbuffer(newLines);
      return;
    }
    if (start >= screenStart) {
      this.backbuffer.splice(start, deleteCount, ...newLines);
      return;
    }
    this.isTainted = true;
  }
  syncLines(lines) {
    const backBufferLength = Math.max(0, lines.length - this.rows);
    for (const [i, line] of lines.entries()) {
      if (i < backBufferLength) {
        const clampedLine = this.clampLine(line.styledChars, this.columns);
        this.backbuffer.push(clampedLine);
        if (this.backbuffer.length > this.maxScrollbackLength) {
          this.backbuffer.shift();
        }
      } else {
        const screenRow = i - backBufferLength;
        this.syncLine(line, screenRow);
      }
    }
    this.firstRender = false;
  }
  writeLines(lines) {
    if (this.backbuffer.length > 0 || this.screen.length > 0) {
      throw new Error(`writeLines can only be called on an empty terminal. Sizes = ${this.backbuffer.length}, ${this.screen.length}`);
    }
    const backBufferLength = Math.max(0, lines.length - this.rows);
    for (const [i, line] of lines.entries()) {
      const clampedLine = this.clampLine(line.styledChars, this.columns);
      let textToWrite = clampedLine.text;
      if (this.debugRainbowColor) {
        textToWrite = colorize_default(textToWrite, this.debugRainbowColor, "background");
      }
      this.writeHelper(textToWrite);
      this.linesUpdated++;
      if (i >= backBufferLength && i < backBufferLength + this.rows && this.isFirstRender && clampedLine.length < this.columns) {
        this.writeHelper(base_exports.eraseEndLine);
      }
      if (i + 1 < lines.length) {
        this.writeHelper("\n");
      }
      if (i < backBufferLength) {
        this.backbuffer.push(clampedLine);
        if (this.backbuffer.length > this.maxScrollbackLength) {
          this.backbuffer.shift();
        }
      } else {
        this.screen.push(clampedLine);
      }
    }
    if (this.isFirstRender) {
      for (let row = lines.length; row < this.rows; row++) {
        this.writeHelper("\n" + base_exports.eraseEndLine);
      }
    }
    this.cursorX = -1;
    this.cursorY = -1;
    this.firstRender = false;
    this.finishChunkAndUpdateCursor();
  }
  setTargetCursorPosition(row, col) {
    if (this.targetCursorY === row && this.targetCursorX === col) {
      return;
    }
    this.targetCursorY = row;
    this.targetCursorX = col;
  }
  getExpectedState() {
    return {
      backbuffer: [...this.backbuffer],
      screen: [...this.screen],
      cursorX: this.cursorX,
      cursorY: this.cursorY
    };
  }
  finish() {
    this.finishChunkAndUpdateCursor();
    this.targetCursorY = -1;
    this.targetCursorX = -1;
  }
  done() {
    this.finishChunkAndUpdateCursor();
    this.unkownCursorLocation();
    this.resetScrollRegion();
    if (this.screen.length > 0) {
      this.moveCursor(this.rows - 1, 0);
      this.writeHelper("\n");
      this.cursorX = 0;
      this.cursorY = this.rows;
    }
    this.finishChunkAndUpdateCursor();
    this.flush();
    this.isDone = true;
  }
  moveCursor(x, y) {
    if (x === this.cursorY && y === this.cursorX) {
      return;
    }
    const diff = x - this.cursorY;
    if (this.cursorY < 0 || this.cursorX < 0 || x !== this.cursorY || y !== this.cursorX) {
      this.writeHelper(base_exports.cursorTo(y, x));
      this.cursorY = x;
      this.cursorX = y;
      return;
    }
    if (diff > 0) {
      this.writeHelper(getMoveCursorDownCode(diff));
    } else if (diff < 0) {
      this.writeHelper(getMoveCursorUpCode(-diff));
    }
    this.cursorY = x;
    if (y !== this.cursorX) {
      if (y === 0) {
        this.writeHelper(base_exports.cursorLeft);
      } else {
        this.writeHelper(base_exports.cursorTo(y));
      }
      this.cursorX = y;
    }
  }
  clampLine(line, width) {
    if (width <= 0 || !line) {
      return {
        styledChars: new StyledLine(),
        text: "",
        length: 0,
        tainted: false
      };
    }
    let i = line.length - 1;
    while (i >= 0 && line.getValue(i) === " " && !line.hasStyles(i)) {
      i--;
    }
    const trimmedLength = i + 1;
    let visualWidth = 0;
    for (let k = 0; k < trimmedLength; k++) {
      const val = line.getValue(k);
      if (val === "")
        continue;
      visualWidth += line.getFullWidth(k) ? 2 : 1;
    }
    if (visualWidth <= width) {
      const styledChars2 = trimmedLength === line.length ? line : line.slice(0, trimmedLength);
      return {
        styledChars: styledChars2,
        text: styledLineToString(styledChars2),
        length: visualWidth,
        tainted: false
      };
    }
    const lastVal = line.getValue(i);
    const lastFullWidth = line.getFullWidth(i);
    const hasBoxChar = lastVal === "\u256E" || lastVal === "\u2502" || lastVal === "\u256F";
    let targetVisualWidth = width;
    if (hasBoxChar) {
      targetVisualWidth -= lastFullWidth ? 2 : 1;
    }
    let currentWidth = 0;
    let sliceIndex = 0;
    for (let k = 0; k < trimmedLength; k++) {
      const charWidth = line.getFullWidth(k) ? 2 : 1;
      if (currentWidth + charWidth > targetVisualWidth) {
        break;
      }
      currentWidth += charWidth;
      sliceIndex++;
    }
    if (hasBoxChar) {
      const boxWidth = lastFullWidth ? 2 : 1;
      const lastCharLine = new StyledLine();
      lastCharLine.pushChar(lastVal, line.getFormatFlags(i), line.getFgColor(i), line.getBgColor(i), line.getLink(i));
      const styledChars2 = line.slice(0, sliceIndex).combine(lastCharLine);
      return {
        styledChars: styledChars2,
        text: styledLineToString(styledChars2),
        length: currentWidth + boxWidth,
        tainted: false
      };
    }
    const styledChars = line.slice(0, sliceIndex);
    return {
      styledChars,
      text: styledLineToString(styledChars),
      length: currentWidth,
      tainted: false
    };
  }
  syncLine(line, y) {
    if (y < 0 || y >= this.rows) {
      return;
    }
    const clampedLine = this.clampLine(line.styledChars, this.columns);
    const currentLine = this.screen[y];
    if (currentLine && !currentLine.tainted && currentLine.text === clampedLine.text) {
      return;
    }
    this.moveCursor(y, 0);
    this.linesUpdated++;
    let textToWrite = clampedLine.text;
    if (this.debugRainbowColor) {
      textToWrite = colorize_default(textToWrite, this.debugRainbowColor, "background");
    }
    this.writeHelper(textToWrite);
    if (clampedLine.length < this.columns) {
      this.writeHelper(base_exports.eraseEndLine);
    }
    if (y !== this.rows - 1 && y !== this.scrollRegionBottom - 1) {
      this.writeHelper("\n");
      this.cursorY = y + 1;
      this.cursorX = -1;
    } else {
      this.cursorY = y;
      this.cursorX = clampedLine.length;
    }
    clampedLine.tainted = false;
    this.screen[y] = clampedLine;
  }
  scrollLines(options) {
    try {
      this.performScroll(options);
    } finally {
      this.resetScrollRegion();
    }
  }
  resize(columns, rows) {
    if (this.columns === columns && this.rows === rows) {
      return;
    }
    this.columns = columns;
    this.rows = rows;
    const startIndex = Math.max(0, this.backbuffer.length - this.rows);
    for (let i = startIndex; i < this.backbuffer.length; i++) {
      const line = this.backbuffer[i];
      if (line && line.length >= this.columns) {
        line.tainted = true;
      }
    }
    for (const line of this.screen) {
      if (line) {
        line.tainted = true;
      }
    }
  }
  clear(_options) {
    if (process5.env["TERM_PROGRAM"] === "vscode" && this.forceScrollToBottomOnBackbufferRefresh) {
      this.writeHelper(ris);
    } else if (process5.env["TERM_PROGRAM"] === "iTerm.app") {
      this.writeHelper(base_exports.clearTerminal);
    } else {
      this.writeHelper(clearScrollbackStandard);
      this.writeHelper(homeEraseDown);
    }
    this.writeHelper(resetScrollRegion);
    this.scrollRegionTop = -1;
    this.scrollRegionBottom = -1;
    this.screen = [];
    this.backbuffer = [];
    this.firstRender = true;
    this.backbufferDirty = false;
    this.backbufferDirtyCurrentFrame = false;
    if (this.fullRenderTimeout) {
      clearTimeout(this.fullRenderTimeout);
      this.fullRenderTimeout = void 0;
    }
    this.cursorX = -1;
    this.cursorY = -1;
  }
  startSynchronizedOutput() {
    this.writeHelper(enterSynchronizedOutput);
  }
  endSynchronizedOutput() {
    this.writeHelper(exitSynchronizedOutput);
    this.finishChunkAndUpdateCursor();
  }
  flush() {
    if (this.isDone)
      return;
    if (this.cancelSlowFlush) {
      this.cancelSlowFlush();
    }
    this.finishChunkAndUpdateCursor();
    if (this.outputBuffer.length > 0) {
      this.synchronizedWrite(this.outputBuffer.join(""));
    }
    this.firstRender = false;
    this.outputBuffer = [];
  }
  /**
   * Testing only method that flushes content slowly to simplify debugging
   * hard to diagnose issues.
   *
   * If there are bugs in terminal-writer a good way to debug is to call
   * slowFlush instead of flush() so you can see the incremental states the
   * terminal goes through applying the changes.
   */
  async slowFlush() {
    if (this.isDone)
      return;
    if (this.cancelSlowFlush) {
      this.cancelSlowFlush();
    }
    this.finishChunkAndUpdateCursor();
    if (this.outputBuffer.length === 0) {
      return;
    }
    this.firstRender = false;
    while (this.outputBuffer.length > 0) {
      const chunk = this.outputBuffer.shift();
      if (chunk) {
        this.synchronizedWrite(chunk);
      }
      await new Promise((resolve) => {
        let finished = false;
        const timer = setTimeout(() => {
          finished = true;
          this.cancelSlowFlush = void 0;
          resolve();
        }, 50);
        this.cancelSlowFlush = () => {
          if (!finished) {
            clearTimeout(timer);
            finished = true;
            if (this.outputBuffer.length > 0) {
              this.synchronizedWrite(this.outputBuffer.join(""));
              this.outputBuffer = [];
            }
            this.cancelSlowFlush = void 0;
            resolve();
          }
        };
      });
    }
  }
  validateLinesConsistent(lines) {
    if (this.isTainted) {
      return;
    }
    for (let r = 0; r < this.rows; r++) {
      const index = lines.length + r - this.rows;
      if (index < 0) {
        continue;
      }
      if (!linesEqual(this.screen[r]?.styledChars, lines[index]?.styledChars) && debugWorker) {
        debugLog(`Line ${r} on screen inconsistent between terminalWriter and ground truth. Expected "${styledLineToString(lines[index]?.styledChars ?? new StyledLine())}", got "${styledLineToString(this.screen[r]?.styledChars ?? new StyledLine())}"`);
      }
    }
    const backbufferLimit = lines.length - this.rows;
    for (let i = 0; i < backbufferLimit; i++) {
      if (!linesEqual(this.backbuffer[i]?.styledChars, lines[i]?.styledChars) && debugWorker) {
        debugLog(`Line ${i} in backbuffer inconsistent. Expected "${styledLineToString(lines[i]?.styledChars ?? new StyledLine())}", got "${styledLineToString(this.backbuffer[i]?.styledChars ?? new StyledLine())}"`);
      }
    }
  }
  shiftScreenUp(start, bottom) {
    for (let i = start; i < bottom - 1; i++) {
      this.screen[i] = this.screen[i + 1];
    }
    this.screen[bottom - 1] = {
      styledChars: new StyledLine(),
      text: "",
      length: 0,
      tainted: false
    };
  }
  /**
   * Trigger a scroll up of content into the backbuffer.
   */
  applyScrollUpBackbuffer(start, bottom) {
    this.moveCursor(bottom - 1, 0);
    this.writeHelper("\n");
    this.cursorX = -1;
    this.cursorY = bottom - 1;
    if (start === 0) {
      this.backbuffer.push(this.screen[0]);
      if (this.backbuffer.length > this.maxScrollbackLength) {
        this.backbuffer.shift();
      }
    }
    this.shiftScreenUp(start, bottom);
  }
  applyScrollUp(start, bottom) {
    if (start === 0 && platform2.isAppleTerminal() && bottom > 1) {
      const line0Content = this.screen[1];
      this.writeHelper(getSetScrollRegionCode(1, bottom));
      this.scrollRegionTop = 1;
      this.scrollRegionBottom = bottom;
      this.moveCursor(1, 0);
      this.writeHelper(getDeleteLinesCode(1));
      this.shiftScreenUp(1, bottom);
      if (line0Content) {
        this.screen[0] = { ...line0Content, tainted: true };
      } else {
        this.screen[0] = {
          styledChars: new StyledLine(),
          text: "",
          length: 0,
          tainted: true
        };
      }
      return;
    }
    this.moveCursor(start, 0);
    this.writeHelper(getDeleteLinesCode(1));
    this.shiftScreenUp(start, bottom);
  }
  applyScrollDown(start, bottom) {
    this.moveCursor(start, 0);
    this.writeHelper(getInsertLinesCode(1));
    for (let i = bottom - 1; i > start; i--) {
      this.screen[i] = this.screen[i - 1];
    }
    this.screen[start] = {
      styledChars: new StyledLine(),
      text: "",
      length: 0,
      tainted: false
    };
  }
  performScroll(options) {
    const { start, end, linesToScroll, lines, direction, scrollToBackbuffer } = options;
    if (debugWorker) {
      debugLog(`[terminal-writer] SCROLLING LINES ${start}-${end} by ${linesToScroll} ${direction}`);
    }
    this.setScrollRegion(start, end);
    const scrollAreaHeight = end - start;
    if (lines.length !== end - start + linesToScroll) {
      throw new Error(`Mismatch in scrollLines: expected ${end - start + linesToScroll} lines, got ${lines.length}`);
    }
    if (scrollToBackbuffer && direction !== "up") {
      throw new Error(`scrollToBackbuffer is only supported for direction "up"`);
    }
    const existingContentOffset = direction === "up" ? 0 : linesToScroll;
    for (let i = start; i < end; i++) {
      this.syncLine(lines[existingContentOffset + i - start], i);
    }
    if (direction === "up") {
      for (let i = 0; i < linesToScroll; i++) {
        if (scrollToBackbuffer) {
          if (start > 0) {
            this.setScrollRegion(0, this.rows);
            const savedHeader = this.screen.slice(0, start);
            const savedFooter = this.screen.slice(end, this.rows);
            this.syncLine(lines[i], 0);
            this.applyScrollUpBackbuffer(0, this.rows);
            for (const [k, element] of savedHeader.entries()) {
              this.syncLine(element, k);
            }
            for (const [k, element] of savedFooter.entries()) {
              this.syncLine(element, end + k);
            }
          } else {
            this.setScrollRegion(0, end);
            this.syncLine(lines[i], 0);
            this.applyScrollUpBackbuffer(0, end);
          }
        } else {
          this.applyScrollUp(start, end);
        }
        this.unkownCursorLocation();
        this.syncLine(lines[i + scrollAreaHeight], end - 1);
      }
      this.finishChunkAndUpdateCursor();
    } else if (direction === "down") {
      for (let i = 0; i < linesToScroll; i++) {
        const line = lines[linesToScroll - 1 - i];
        this.applyScrollDown(start, end);
        this.unkownCursorLocation();
        this.syncLine(line, start);
      }
      this.finishChunkAndUpdateCursor();
    }
  }
  synchronizedWrite(text) {
    if (this.enableSynchronizedOutput) {
      this.stdout.write(enterSynchronizedOutput + text + exitSynchronizedOutput);
    } else {
      this.stdout.write(text);
    }
  }
  resetScrollRegion() {
    if (this.scrollRegionTop !== -1 || this.scrollRegionBottom !== -1) {
      this.writeHelper(resetScrollRegion);
      this.unkownCursorLocation();
      this.scrollRegionTop = -1;
      this.scrollRegionBottom = -1;
    }
  }
  setScrollRegion(top, bottom) {
    if (this.scrollRegionTop !== top || this.scrollRegionBottom !== bottom) {
      this.writeHelper(getSetScrollRegionCode(top, bottom));
      this.unkownCursorLocation();
      this.scrollRegionTop = top;
      this.scrollRegionBottom = bottom;
    }
  }
  writeHelper(text) {
    if (this.isDone) {
      return;
    }
    this.currentChunkBuffer.push(text);
  }
  finishChunkAndUpdateCursor() {
    if (this.targetCursorY >= 0 && this.targetCursorX >= 0) {
      this.moveCursor(this.targetCursorY, this.targetCursorX);
    }
    if (this.currentChunkBuffer.length > 0) {
      this.outputBuffer.push(this.currentChunkBuffer.join(""));
      this.currentChunkBuffer = [];
    }
  }
};

// node_modules/ink/build/worker/canvas.js
var Canvas = class _Canvas {
  width;
  height;
  lines;
  /**
   * Creates a new Canvas from a set of lines.
   */
  static fromLines(width, height, lines) {
    return new _Canvas(width, height, lines);
  }
  /**
   * Creates an empty Canvas with the given dimensions.
   */
  static create(width, height, tainted = false) {
    const lines = [];
    for (let i = 0; i < height; i++) {
      lines.push({
        styledChars: new StyledLine(),
        text: "",
        length: 0,
        tainted
      });
    }
    return new _Canvas(width, height, lines);
  }
  constructor(width, height, lines) {
    this.width = width;
    this.height = height;
    this.lines = lines;
  }
  /**
   * Returns the character at the given coordinates.
   */
  getChar(x, y) {
    if (y < 0 || y >= this.height || x < 0 || x >= this.width) {
      return void 0;
    }
    const line = this.lines[y];
    if (!line || x >= line.styledChars.length) {
      return void 0;
    }
    return { bgColor: line.styledChars.getBgColor(x) };
  }
  /**
   * Sets a character at the given coordinates, respecting clipping.
   */
  // eslint-disable-next-line max-params
  setChar(x, y, value, formatFlags, fgColor, bgColor, link2, clip) {
    if (y < 0 || y >= this.height || x < 0 || x >= this.width) {
      return;
    }
    if (clip && (x < clip.x || x >= clip.x + clip.w || y < clip.y || y >= clip.y + clip.h)) {
      return;
    }
    const line = this.lines[y];
    if (!line) {
      return;
    }
    while (line.styledChars.length <= x) {
      line.styledChars.pushChar(" ", 0);
    }
    line.styledChars.setChar(x, value, formatFlags, fgColor, bgColor, link2);
  }
  /**
   * Draws a sequence of characters starting at (x, y).
   */
  drawStyledChars(x, y, chars, clip) {
    for (let i = 0; i < chars.length; i++) {
      this.setChar(x + i, y, chars.getValue(i), chars.getFormatFlags(i), chars.getFgColor(i), chars.getBgColor(i), chars.getLink(i), clip);
    }
  }
  /**
   * Returns the underlying lines.
   */
  getLines() {
    return this.lines;
  }
};

// node_modules/ink/build/worker/scene-manager.js
import { Buffer as Buffer4 } from "node:buffer";
var SceneManager = class {
  regions = /* @__PURE__ */ new Map();
  root;
  regionWasAtEnd = /* @__PURE__ */ new Map();
  /**
   * Updates the scene tree and regions with new data.
   * Returns true if the scene was updated in a way that likely requires a re-render.
   */
  update(tree, updates, options) {
    this.root = tree;
    const activeIds = /* @__PURE__ */ new Set();
    const traverse = (node) => {
      activeIds.add(node.id);
      for (const child of node.children) {
        traverse(child);
      }
    };
    traverse(tree);
    for (const id of this.regions.keys()) {
      if (!activeIds.has(id)) {
        this.regions.delete(id);
        this.regionWasAtEnd.delete(id);
        options.onRegionDeleted?.(id);
      }
    }
    for (const update of updates) {
      let region = this.regions.get(update.id);
      const isNew = !region;
      if (!region) {
        region = {
          id: update.id,
          selectableSpans: [],
          x: 0,
          y: 0,
          width: 0,
          height: 0,
          lines: [],
          styledOutput: [],
          isScrollable: false,
          stickyHeaders: [],
          children: []
        };
        this.regions.set(update.id, region);
        this.regionWasAtEnd.set(update.id, true);
      }
      const r = region;
      for (const key of regionLayoutProperties) {
        if (update[key] !== void 0) {
          if (key === "scrollTop") {
            options.onScrollUpdate(r.id, update.scrollTop, isNew);
          } else {
            copyRegionProperty(r, update, key);
          }
        }
      }
      if (update.stickyHeaders !== void 0) {
        r.stickyHeaders = update.stickyHeaders.map((header) => ({
          ...header,
          lines: new Deserializer(Buffer4.from(header.lines)).deserialize(),
          stuckLines: header.stuckLines ? new Deserializer(Buffer4.from(header.stuckLines)).deserialize() : void 0,
          styledOutput: new Deserializer(Buffer4.from(header.styledOutput)).deserialize()
        }));
      }
      if (update.lines) {
        const mutableLines = r.lines;
        while (mutableLines.length < update.lines.totalLength) {
          mutableLines.push(new StyledLine());
        }
        if (mutableLines.length > update.lines.totalLength) {
          mutableLines.length = update.lines.totalLength;
        }
        for (const chunk of update.lines.updates) {
          const deserializer = new Deserializer(Buffer4.from(chunk.data));
          const chunkLines = deserializer.deserialize();
          for (const [i, line] of chunkLines.entries()) {
            mutableLines[chunk.start + i] = line;
          }
        }
      }
    }
    return updates.length > 0;
  }
  getRegion(id) {
    return this.regions.get(id);
  }
  getRootRegion() {
    return this.root ? this.regions.get(this.root.id) : void 0;
  }
};

// node_modules/ink/build/worker/animation-controller.js
var AnimationController = class {
  options;
  targetScrollTops = /* @__PURE__ */ new Map();
  intervalId;
  idleResolvers = [];
  constructor(options) {
    this.options = options;
  }
  /**
   * Updates the animation interval.
   */
  updateInterval(interval) {
    this.options.interval = interval;
  }
  /**
   * Returns the internal target scroll tops map.
   */
  get allTargetScrollTops() {
    return this.targetScrollTops;
  }
  /**
   * Returns true if the animation loop is running.
   */
  get isRunning() {
    return this.intervalId !== void 0;
  }
  /**
   * Returns a promise that resolves when the animation loop stops.
   */
  async waitForIdle() {
    if (!this.isRunning) {
      return;
    }
    return new Promise((resolve) => {
      this.idleResolvers.push(resolve);
    });
  }
  /**
   * Sets the target scroll position for a region.
   */
  setTargetScrollTop(regionId, scrollTop) {
    this.targetScrollTops.set(regionId, scrollTop);
  }
  /**
   * Returns the target scroll top for a region.
   */
  getTargetScrollTop(regionId) {
    return this.targetScrollTops.get(regionId);
  }
  /**
   * Removes the target scroll position for a region.
   */
  deleteTargetScrollTop(regionId) {
    this.targetScrollTops.delete(regionId);
  }
  /**
   * Starts the animation loop if not already running.
   */
  start() {
    if (this.intervalId) {
      return;
    }
    this.intervalId = setInterval(() => {
      this.tick();
    }, this.options.interval);
  }
  /**
   * Stops the animation loop.
   */
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = void 0;
    }
    for (const resolve of this.idleResolvers) {
      resolve();
    }
    this.idleResolvers = [];
  }
  /**
   * Interrupts animations and jumps all regions to their targets.
   */
  jumpToTargets(regions) {
    for (const [id, target] of this.targetScrollTops) {
      const region = regions.get(id);
      if (region) {
        region.scrollTop = target;
      }
    }
    this.stop();
  }
  /**
   * Updates regions based on their targets. Returns true if any region scrolled.
   */
  updateRegions(regions) {
    let hasScrolled = false;
    let canScrollMore = false;
    for (const region of regions.values()) {
      const target = this.targetScrollTops.get(region.id);
      if (target === void 0) {
        continue;
      }
      const current = region.scrollTop ?? 0;
      if (current !== target) {
        region.scrollTop = current < target ? current + 1 : current - 1;
        hasScrolled = true;
        canScrollMore = true;
      }
    }
    return { hasScrolled, canScrollMore };
  }
  /**
   * Processes one frame of animation.
   */
  tick() {
    this.options.onTick();
  }
};

// node_modules/ink/build/worker/compositor.js
var Compositor = class _Compositor {
  options;
  static lastBackgroundColor;
  static lastBackgroundStyles;
  constructor(options) {
    this.options = options;
  }
  drawContent(canvas, region, absX, absY, clip) {
    const scrollTop = region.scrollTop ?? 0;
    const scrollLeft = region.scrollLeft ?? 0;
    const isOpaque = Boolean(region.opaque) || Boolean(region.backgroundColor);
    for (let sy = clip.y; sy < clip.y + clip.h; sy++) {
      if (sy < 0 || sy >= canvas.height) {
        continue;
      }
      const dy = sy - absY;
      const contentY = Math.round(scrollTop + dy);
      const line = region.lines[contentY];
      if (!line) {
        continue;
      }
      const startSx = Math.round(clip.x);
      const endSx = Math.round(clip.x + clip.w);
      for (let sx = startSx; sx < endSx; sx++) {
        if (sx < 0 || sx >= canvas.width) {
          continue;
        }
        const dx = sx - absX;
        const contentX = scrollLeft + dx;
        if (contentX < line.length) {
          const val = line.getValue(contentX);
          const isEmpty = val === " " && !line.hasStyles(contentX);
          if (isEmpty) {
            if (!isOpaque) {
              continue;
            }
            if (region.backgroundColor) {
              const bgColor = this.getBackgroundStyles(region.backgroundColor);
              if (bgColor) {
                canvas.setChar(sx, sy, val, line.getFormatFlags(contentX), line.getFgColor(contentX), bgColor, line.getLink(contentX));
                continue;
              }
            }
          }
          canvas.setChar(sx, sy, val, line.getFormatFlags(contentX), line.getFgColor(contentX), line.getBgColor(contentX), line.getLink(contentX));
        }
      }
    }
  }
  drawStickyHeaders(canvas, region, absX, absY, clip) {
    if (this.options.skipStickyHeaders) {
      return;
    }
    const scrollTop = region.scrollTop ?? 0;
    for (const header of region.stickyHeaders) {
      const useStuckPosition = this.isHeaderStuck(header, absY, scrollTop, region);
      if (!useStuckPosition) {
        continue;
      }
      const linesToRender = header.stuckLines ?? header.lines;
      let headerY = absY + header.y;
      const headerH = linesToRender.length;
      if (this.options.stickyHeadersInBackbuffer && region.overflowToBackbuffer) {
        if (header.type === "top") {
          if (headerY < 0 && absY + region.height > 0) {
            headerY = 0;
          }
        } else if (header.type === "bottom") {
          const stuckPos = this.options.canvasHeight - (header.stuckLines ?? header.lines).length;
          if (headerY > stuckPos && absY < stuckPos + headerH) {
            headerY = stuckPos;
          }
        }
      }
      if (header.type === "top" && header.maxStuckY !== void 0) {
        const absoluteMaxStuckY = absY + header.maxStuckY;
        if (headerY > absoluteMaxStuckY) {
          headerY = absoluteMaxStuckY;
        }
      } else if (header.type === "bottom" && header.minStuckY !== void 0) {
        const absoluteMinStuckY = absY + header.minStuckY;
        if (headerY < absoluteMinStuckY) {
          headerY = absoluteMinStuckY;
        }
      }
      for (let i = 0; i < headerH; i++) {
        const sy = Math.round(headerY + i);
        const withinRegionClip = sy >= clip.y && sy < clip.y + clip.h;
        const aboveRegionAndStickyEnabled = header.type === "top" && absY < 0 && this.options.stickyHeadersInBackbuffer && region.overflowToBackbuffer && sy >= 0 && sy < Math.min(canvas.height, absY + region.height);
        const belowRegionAndStickyEnabled = header.type === "bottom" && absY + region.height > this.options.canvasHeight && this.options.stickyHeadersInBackbuffer && region.overflowToBackbuffer && sy >= Math.max(0, absY) && sy < this.options.canvasHeight;
        if (!withinRegionClip && !aboveRegionAndStickyEnabled && !belowRegionAndStickyEnabled) {
          continue;
        }
        if (sy < 0 || sy >= canvas.height) {
          continue;
        }
        const line = linesToRender[i];
        if (!line) {
          continue;
        }
        const headerX = Math.round(header.x + absX);
        const headerW = Math.round(line.length);
        const hx1 = Math.max(headerX, clip.x);
        const hx2 = Math.min(headerX + headerW, clip.x + clip.w);
        for (let sx = hx1; sx < hx2; sx++) {
          const cx = sx - headerX;
          if (cx < line.length) {
            canvas.setChar(sx, sy, line.getValue(cx), line.getFormatFlags(cx), line.getFgColor(cx), line.getBgColor(cx), line.getLink(cx));
          }
        }
      }
    }
  }
  drawScrollbars(canvas, region, absX, absY, clip) {
    if (Boolean(this.options.skipScrollbars && region.overflowToBackbuffer) || !region.isScrollable || region.scrollbarVisible === false) {
      return;
    }
    const scrollTop = region.scrollTop ?? 0;
    const scrollLeft = region.scrollLeft ?? 0;
    const scrollHeight = region.scrollHeight ?? 0;
    const scrollWidth = region.scrollWidth ?? 0;
    const isVerticalScrollbarVisible = (region.isVerticallyScrollable ?? false) && scrollHeight > region.height;
    const isHorizontalScrollbarVisible = (region.isHorizontallyScrollable ?? false) && scrollWidth > region.width;
    if (isVerticalScrollbarVisible) {
      let scrollPosition = scrollTop;
      const targetScrollTop = this.options.targetScrollTops.get(region.id);
      if (this.options.animatedScroll && targetScrollTop !== void 0 && targetScrollTop !== scrollTop) {
        const wasAtEnd = this.options.regionWasAtEnd.get(region.id);
        const isTargetAtEnd = targetScrollTop >= scrollHeight - region.height;
        if (wasAtEnd && isTargetAtEnd) {
          scrollPosition = targetScrollTop;
        }
      }
      const { startIndex, endIndex, thumbStartHalf, thumbEndHalf } = calculateScrollbarThumb({
        scrollbarDimension: region.height,
        clientDimension: region.height,
        scrollDimension: scrollHeight,
        scrollPosition,
        axis: "vertical"
      });
      const barX = absX + region.width - 1 - (region.marginRight ?? 0);
      renderScrollbar({
        layout: {
          x: barX,
          y: absY,
          width: 1,
          height: region.height,
          thumb: {
            x: barX,
            y: absY + startIndex,
            width: 1,
            height: endIndex - startIndex,
            start: startIndex,
            end: endIndex,
            startHalf: thumbStartHalf,
            endHalf: thumbEndHalf
          }
        },
        clip,
        axis: "vertical",
        color: region.scrollbarThumbColor,
        setChar(x, y, value, formatFlags, fgColor, bgColor, link2) {
          canvas.setChar(x, y, value, formatFlags, fgColor, bgColor, link2);
        },
        getExistingChar(x, y) {
          return canvas.getChar(x, y);
        }
      });
    }
    if (isHorizontalScrollbarVisible) {
      const scrollbarWidth = region.width - (isVerticalScrollbarVisible ? 1 : 0);
      const { startIndex, endIndex, thumbStartHalf, thumbEndHalf } = calculateScrollbarThumb({
        scrollbarDimension: scrollbarWidth,
        clientDimension: region.width,
        scrollDimension: scrollWidth,
        scrollPosition: scrollLeft,
        axis: "horizontal"
      });
      const barY = absY + region.height - 1 - (region.marginBottom ?? 0);
      renderScrollbar({
        layout: {
          x: absX,
          y: barY,
          width: scrollbarWidth,
          height: 1,
          thumb: {
            x: absX + startIndex,
            y: barY,
            width: endIndex - startIndex,
            height: 1,
            start: startIndex,
            end: endIndex,
            startHalf: thumbStartHalf,
            endHalf: thumbEndHalf
          }
        },
        clip,
        axis: "horizontal",
        color: region.scrollbarThumbColor,
        setChar(x, y, value, formatFlags, fgColor, bgColor, link2) {
          canvas.setChar(x, y, value, formatFlags, fgColor, bgColor, link2);
        },
        getExistingChar(x, y) {
          return canvas.getChar(x, y);
        }
      });
    }
  }
  isHeaderStuck(header, absY, scrollTop, region) {
    const isStuckState = header.type === "bottom" ? Math.round(header.naturalRow - scrollTop + header.lines.length) >= Math.round(header.y + (header.stuckLines ?? header.lines).length) : Math.round(header.naturalRow - scrollTop) <= Math.round(header.y);
    if (!isStuckState) {
      return false;
    }
    if (header.type === "top") {
      if (region.overflowToBackbuffer && absY + header.y <= 0 && !(this.options.stickyHeadersInBackbuffer ?? false)) {
        return false;
      }
      return true;
    }
    return true;
  }
  calculateActualStuckTopHeight(region, absY, scrollTop) {
    let stuckHeight = 0;
    const topHeaders = [...region.stickyHeaders].filter((h) => h.type === "top").sort((a, b) => a.y - b.y);
    for (const header of topHeaders) {
      if (this.isHeaderStuck(header, absY, scrollTop, region) && Math.abs(Math.round(header.y) - stuckHeight) < 0.5) {
        const linesToRender = header.stuckLines ?? header.lines;
        stuckHeight += linesToRender.length;
      } else if (this.isHeaderStuck(header, absY, scrollTop, region)) {
        break;
      }
    }
    return stuckHeight;
  }
  calculateActualStuckBottomHeight(region, absY, scrollTop) {
    let stuckHeight = 0;
    const bottomHeaders = [...region.stickyHeaders].filter((h) => h.type === "bottom").sort((a, b) => b.y - a.y);
    for (const header of bottomHeaders) {
      if (this.isHeaderStuck(header, absY, scrollTop, region)) {
        const linesToRender = header.stuckLines ?? header.lines;
        const footerRowInRegion = region.height - linesToRender.length - stuckHeight;
        if (Math.round(header.y) === Math.round(footerRowInRegion)) {
          stuckHeight += linesToRender.length;
        } else {
          break;
        }
      }
    }
    return stuckHeight;
  }
  getBackgroundStyles(color) {
    if (color === _Compositor.lastBackgroundColor) {
      return _Compositor.lastBackgroundStyles;
    }
    const styles4 = getBackgroundColorEscape(color);
    _Compositor.lastBackgroundColor = color;
    _Compositor.lastBackgroundStyles = styles4;
    return styles4;
  }
};

// node_modules/ink/build/worker/scroll-optimizer.js
var ScrollOptimizer = class {
  maxRegionScrollTops = /* @__PURE__ */ new Map();
  lastRegionScrollTops = /* @__PURE__ */ new Map();
  /**
   * Determines if a region scroll can be optimized with hardware scrolling.
   */
  calculateScrollOperations(region, rows, columns, cameraY, getLinesForScroll, calculateStuckTopHeight, calculateStuckBottomHeight, stickyHeadersInBackbuffer) {
    if (!region.isScrollable) {
      this.lastRegionScrollTops.delete(region.id);
      return [];
    }
    const scrollTop = region.scrollTop ?? 0;
    if (!this.lastRegionScrollTops.has(region.id)) {
      this.lastRegionScrollTops.set(region.id, scrollTop);
      if (region.overflowToBackbuffer) {
        this.updateMaxPushed(region.id, scrollTop);
      }
      return [];
    }
    const lastScrollTop = this.lastRegionScrollTops.get(region.id) ?? 0;
    if (scrollTop === lastScrollTop) {
      return [];
    }
    const absY = Math.round(region.y - cameraY);
    const start = Math.max(0, absY);
    const regionHeight = Math.round(region.height);
    const end = Math.min(rows, absY + regionHeight);
    const actualStuckTopHeight = calculateStuckTopHeight(region, absY, scrollTop);
    const actualStuckBottomHeight = calculateStuckBottomHeight(region, absY, scrollTop);
    const adjustedStart = Math.round(Math.max(start, absY + (region.overflowToBackbuffer && !stickyHeadersInBackbuffer ? 0 : actualStuckTopHeight)));
    const adjustedEnd = Math.round(Math.min(end, absY + regionHeight - actualStuckBottomHeight));
    if (adjustedEnd < adjustedStart) {
      this.lastRegionScrollTops.set(region.id, scrollTop);
      return [];
    }
    const maxPushed = this.maxRegionScrollTops.get(region.id) ?? 0;
    const direction = scrollTop > lastScrollTop ? "up" : "down";
    const linesToScroll = Math.abs(scrollTop - lastScrollTop);
    const operations = [];
    if (direction === "up" && region.overflowToBackbuffer && region.width >= columns && region.x === 0) {
      const newLinesToPush = Math.min(linesToScroll, Math.max(0, scrollTop - maxPushed));
      const linesToJustScroll = linesToScroll - newLinesToPush;
      if (newLinesToPush > 0) {
        const pushBase = Math.max(lastScrollTop, maxPushed);
        operations.push({
          start: adjustedStart,
          end: adjustedEnd,
          linesToScroll: newLinesToPush,
          lines: getLinesForScroll(pushBase, newLinesToPush, adjustedStart, adjustedEnd),
          direction: "up",
          scrollToBackbuffer: true,
          regionId: region.id,
          newMaxPushed: Math.max(maxPushed, scrollTop)
        });
      }
      if (linesToJustScroll > 0) {
        const visualBase = lastScrollTop + newLinesToPush;
        operations.push({
          start: adjustedStart,
          end: adjustedEnd,
          linesToScroll: linesToJustScroll,
          lines: getLinesForScroll(visualBase, linesToJustScroll, adjustedStart, adjustedEnd),
          direction: "up",
          scrollToBackbuffer: false,
          regionId: region.id
        });
      }
    } else {
      operations.push({
        start: adjustedStart,
        end: adjustedEnd,
        linesToScroll,
        lines: getLinesForScroll(direction === "up" ? lastScrollTop : scrollTop, linesToScroll, adjustedStart, adjustedEnd),
        direction,
        scrollToBackbuffer: false,
        regionId: region.id
      });
    }
    this.lastRegionScrollTops.set(region.id, scrollTop);
    return operations;
  }
  updateMaxPushed(regionId, maxPushed) {
    const current = this.maxRegionScrollTops.get(regionId) ?? 0;
    this.maxRegionScrollTops.set(regionId, Math.max(current, maxPushed));
  }
  setMaxPushed(regionId, maxPushed) {
    this.maxRegionScrollTops.set(regionId, maxPushed);
  }
  resetTracking(regionId) {
    this.maxRegionScrollTops.delete(regionId);
    this.lastRegionScrollTops.delete(regionId);
  }
};

// node_modules/ink/build/worker/render-worker.js
var defaultAnimationInterval = 1;
var defaultMaxScrollbackLength = 1e3;
var debugWorker = false;
var clearDebugLogPerFrame = false;
var TerminalBufferWorker = class {
  columns;
  rows;
  frameIndex = 0;
  debugRainbowEnabled = false;
  isAlternateBufferEnabled = false;
  stickyHeadersInBackbuffer = false;
  animatedScroll = false;
  animationInterval = defaultAnimationInterval;
  backbufferUpdateDelay = 1e3;
  maxScrollbackLength = defaultMaxScrollbackLength;
  forceScrollToBottomOnBackbufferRefresh = false;
  resized = false;
  cursorPosition;
  forceNextRender = false;
  isRecording = false;
  recordingFilename = "";
  recordedFrames = [];
  recordingStartTime = 0;
  // Ground truth on what lines should be rendered (composed frame)
  screen = [];
  backbuffer = [];
  renderPromise;
  sceneManager = new SceneManager();
  animationController;
  scrollOptimizer = new ScrollOptimizer();
  primaryTerminalWriter;
  alternateTerminalWriter;
  get terminalWriter() {
    return this.isAlternateBufferEnabled ? this.alternateTerminalWriter : this.primaryTerminalWriter;
  }
  get backbufferDirty() {
    return this.terminalWriter.backbufferDirty;
  }
  set backbufferDirty(value) {
    this.terminalWriter.backbufferDirty = value;
  }
  get backbufferDirtyCurrentFrame() {
    return this.terminalWriter.backbufferDirtyCurrentFrame;
  }
  set backbufferDirtyCurrentFrame(value) {
    this.terminalWriter.backbufferDirtyCurrentFrame = value;
  }
  constructor(columns, rows, options) {
    this.columns = columns;
    this.rows = rows;
    const stdout = options?.stdout ?? process6.stdout;
    this.primaryTerminalWriter = new TerminalWriter(columns, rows, stdout);
    this.alternateTerminalWriter = new TerminalWriter(columns, rows, stdout);
    this.primaryTerminalWriter.writeRaw(base_exports.cursorHide);
    this.alternateTerminalWriter.writeRaw(base_exports.cursorHide);
    this.debugRainbowEnabled = options?.debugRainbowEnabled ?? this.debugRainbowEnabled;
    this.isAlternateBufferEnabled = options?.isAlternateBufferEnabled ?? this.isAlternateBufferEnabled;
    this.stickyHeadersInBackbuffer = options?.stickyHeadersInBackbuffer ?? this.stickyHeadersInBackbuffer;
    this.animatedScroll = options?.animatedScroll ?? this.animatedScroll;
    this.animationInterval = options?.animationInterval ?? this.animationInterval;
    this.backbufferUpdateDelay = options?.backbufferUpdateDelay ?? this.backbufferUpdateDelay;
    this.maxScrollbackLength = options?.maxScrollbackLength ?? this.maxScrollbackLength;
    this.forceScrollToBottomOnBackbufferRefresh = options?.forceScrollToBottomOnBackbufferRefresh ?? this.forceScrollToBottomOnBackbufferRefresh;
    this.primaryTerminalWriter.maxScrollbackLength = this.maxScrollbackLength;
    this.alternateTerminalWriter.maxScrollbackLength = this.maxScrollbackLength;
    this.primaryTerminalWriter.forceScrollToBottomOnBackbufferRefresh = this.forceScrollToBottomOnBackbufferRefresh;
    this.alternateTerminalWriter.forceScrollToBottomOnBackbufferRefresh = this.forceScrollToBottomOnBackbufferRefresh;
    if (this.isAlternateBufferEnabled) {
      this.alternateTerminalWriter.writeRaw(base_exports.enterAlternativeScreen);
    }
    this.animationController = new AnimationController({
      interval: this.animationInterval,
      onTick: () => {
        this.tickAnimation();
      }
    });
  }
  async waitForIdle() {
    await this.flushPendingRender();
    if (this.animatedScroll) {
      await this.animationController.waitForIdle();
    }
    if (this.renderPromise) {
      await this.renderPromise;
    }
  }
  getExpectedState() {
    return this.terminalWriter.getExpectedState();
  }
  getSceneManager() {
    return this.sceneManager;
  }
  startRecording(filename) {
    this.isRecording = true;
    this.recordingFilename = filename;
    this.recordedFrames = [];
    this.recordingStartTime = Date.now();
    const { root } = this.sceneManager;
    if (root) {
      const serializer = new Serializer();
      const updates = this.serializeCurrentRegions(serializer);
      this.recordedFrames.push({
        tree: structuredClone(root),
        updates: updates.map((u) => serializeReplayUpdate(u)),
        cursorPosition: this.cursorPosition,
        timestamp: 0
      });
    }
  }
  stopRecording() {
    if (!this.isRecording)
      return;
    const data = {
      type: "sequence",
      columns: this.columns,
      rows: this.rows,
      frames: this.recordedFrames
    };
    saveReplay(data, this.recordingFilename);
    this.isRecording = false;
    this.recordedFrames = [];
  }
  dumpCurrentFrame(filename) {
    const { root } = this.sceneManager;
    if (!root)
      return;
    const serializer = new Serializer();
    const updates = this.serializeCurrentRegions(serializer);
    const data = {
      type: "single",
      columns: this.columns,
      rows: this.rows,
      frames: [
        {
          tree: root,
          updates: updates.map((u) => serializeReplayUpdate(u)),
          cursorPosition: this.cursorPosition,
          timestamp: 0
        }
      ]
    };
    saveReplay(data, filename);
    const loadedData = {
      type: "single",
      columns: this.columns,
      rows: this.rows,
      frames: [
        {
          tree: root,
          updates,
          cursorPosition: this.cursorPosition,
          timestamp: 0
        }
      ]
    };
    const dumpText = createHumanReadableDump(loadedData);
    fs3.writeFileSync(filename + ".dump.txt", dumpText);
  }
  updateOptions(options) {
    if (options.isAlternateBufferEnabled !== void 0 && this.isAlternateBufferEnabled !== options.isAlternateBufferEnabled) {
      this.terminalWriter.flush();
      if (this.terminalWriter.fullRenderTimeout) {
        clearTimeout(this.terminalWriter.fullRenderTimeout);
        this.terminalWriter.fullRenderTimeout = void 0;
      }
      if (options.isAlternateBufferEnabled) {
        this.primaryTerminalWriter.stdout.write(base_exports.enterAlternativeScreen);
        this.isAlternateBufferEnabled = true;
        this.terminalWriter.clear();
      } else {
        this.alternateTerminalWriter.stdout.write(base_exports.exitAlternativeScreen);
        this.isAlternateBufferEnabled = false;
        this.terminalWriter.unkownCursorLocation();
        this.terminalWriter.taintScreen();
        this.terminalWriter.isTainted = true;
      }
      this.forceNextRender = true;
    }
    if (options.stickyHeadersInBackbuffer !== void 0 && this.stickyHeadersInBackbuffer !== options.stickyHeadersInBackbuffer) {
      this.stickyHeadersInBackbuffer = options.stickyHeadersInBackbuffer;
      this.forceNextRender = true;
    }
    if (options.animatedScroll !== void 0 && this.animatedScroll !== options.animatedScroll) {
      this.animatedScroll = options.animatedScroll;
      if (this.animatedScroll) {
        this.animationController.start();
      } else {
        this.animationController.stop();
      }
    }
    if (options.animationInterval !== void 0 && this.animationInterval !== options.animationInterval) {
      this.animationInterval = options.animationInterval;
      this.animationController.stop();
      this.animationController.updateInterval(this.animationInterval);
      if (this.animatedScroll) {
        this.animationController.start();
      }
    }
    if (options.backbufferUpdateDelay !== void 0) {
      this.backbufferUpdateDelay = options.backbufferUpdateDelay;
    }
    if (options.maxScrollbackLength !== void 0) {
      this.maxScrollbackLength = options.maxScrollbackLength;
      this.primaryTerminalWriter.maxScrollbackLength = this.maxScrollbackLength;
      this.alternateTerminalWriter.maxScrollbackLength = this.maxScrollbackLength;
    }
    if (options.forceScrollToBottomOnBackbufferRefresh !== void 0 && this.forceScrollToBottomOnBackbufferRefresh !== options.forceScrollToBottomOnBackbufferRefresh) {
      this.forceScrollToBottomOnBackbufferRefresh = options.forceScrollToBottomOnBackbufferRefresh;
      this.primaryTerminalWriter.forceScrollToBottomOnBackbufferRefresh = this.forceScrollToBottomOnBackbufferRefresh;
      this.alternateTerminalWriter.forceScrollToBottomOnBackbufferRefresh = this.forceScrollToBottomOnBackbufferRefresh;
    }
  }
  update(tree, updates, cursorPosition) {
    const previousCursorPosition = this.cursorPosition;
    this.cursorPosition = cursorPosition;
    const treeChanged = !this.sceneManager.root || !treesEqual(this.sceneManager.root, tree);
    if (this.isRecording) {
      this.recordedFrames.push({
        tree,
        updates: updates.map((u) => serializeReplayUpdate(u)),
        cursorPosition,
        timestamp: Date.now() - this.recordingStartTime
      });
    }
    if (this.animatedScroll) {
      if (updates.length > 0) {
        if (debugWorker) {
          debugLog(`[RENDER-WORKER] Interrupting animation for jump
`);
        }
        this.animationController.jumpToTargets(this.sceneManager.regions);
      }
      this.animationController.start();
    }
    this.sceneManager.update(tree, updates, {
      animatedScroll: this.animatedScroll,
      onScrollUpdate: (id, scrollTop, isNew) => {
        if (this.animatedScroll && !isNew) {
          this.animationController.setTargetScrollTop(id, scrollTop);
        } else {
          const region = this.sceneManager.getRegion(id);
          if (region) {
            region.scrollTop = scrollTop;
            if (this.animatedScroll) {
              this.animationController.setTargetScrollTop(id, scrollTop);
            }
          }
        }
      },
      onRegionDeleted: (id) => {
        this.animationController.deleteTargetScrollTop(id);
        this.scrollOptimizer.resetTracking(id);
      }
    });
    for (const update of updates) {
      const region = this.sceneManager.getRegion(update.id);
      if (region) {
        const currentEffectiveScrollTop = this.animationController.getTargetScrollTop(region.id) ?? region.scrollTop ?? 0;
        const wasAtEnd = currentEffectiveScrollTop >= (region.scrollHeight ?? 0) - (region.height ?? 0);
        this.sceneManager.regionWasAtEnd.set(region.id, wasAtEnd);
      }
    }
    const rootRegion = this.sceneManager.getRootRegion();
    if (rootRegion) {
      const cameraY = Math.max(0, rootRegion.height - this.rows);
      if (!this.isAlternateBufferEnabled) {
        const maxPushedRoot = this.scrollOptimizer.maxRegionScrollTops.get(rootRegion.id) ?? 0;
        if (cameraY < maxPushedRoot) {
          this.terminalWriter.backbufferScrolledIncorrectly = true;
          this.terminalWriter.backbufferDirtyCurrentFrame = true;
        }
      }
      for (const update of updates) {
        const region = this.sceneManager.getRegion(update.id);
        if (region && update.lines) {
          const scrollTop = region.scrollTop ?? 0;
          for (const chunk of update.lines.updates) {
            if (region.overflowToBackbuffer && chunk.start < scrollTop) {
              this.terminalWriter.backbufferDirty = true;
              this.terminalWriter.backbufferDirtyCurrentFrame = true;
            }
            const absStart = region.y + chunk.start;
            if (absStart < cameraY) {
              this.terminalWriter.backbufferDirty = true;
              this.terminalWriter.backbufferDirtyCurrentFrame = true;
            }
          }
        }
        if (!this.isAlternateBufferEnabled && region && update.scrollTop !== void 0 && region.overflowToBackbuffer) {
          const maxPushed = this.scrollOptimizer.maxRegionScrollTops.get(region.id) ?? 0;
          if (update.scrollTop < maxPushed) {
            this.terminalWriter.backbufferScrolledIncorrectly = true;
            this.terminalWriter.backbufferDirtyCurrentFrame = true;
          }
        }
      }
    }
    const cursorChanged = cursorPosition !== previousCursorPosition && (!cursorPosition || !previousCursorPosition || cursorPosition.row !== previousCursorPosition.row || cursorPosition.col !== previousCursorPosition.col);
    const shouldRender = updates.length > 0 || cursorChanged || treeChanged || this.terminalWriter.backbufferDirty || this.forceNextRender;
    return shouldRender;
  }
  resize(columns, rows) {
    if (this.columns === columns && this.rows === rows) {
      return;
    }
    this.columns = columns;
    this.rows = rows;
    if (debugWorker) {
      debugLog(`XXXXX [RENDER-WORKER] Resize to ${columns}x${rows}
`);
    }
    this.primaryTerminalWriter.resize(columns, rows);
    this.alternateTerminalWriter.resize(columns, rows);
    this.terminalWriter.backbufferDirtyCurrentFrame = true;
    this.resized = true;
    void this.render();
  }
  async fullRender() {
    if (clearDebugLogPerFrame) {
      clearDebugLog();
    }
    if (this.terminalWriter.fullRenderTimeout) {
      clearTimeout(this.terminalWriter.fullRenderTimeout);
      this.terminalWriter.fullRenderTimeout = void 0;
    }
    if (!this.terminalWriter.backbufferDirty) {
      await this.render();
      return;
    }
    if (debugWorker) {
      debugLog(`XXXXX [RENDER-WORKER] True full render triggered
`);
    }
    this.terminalWriter.backbufferDirty = false;
    this.terminalWriter.backbufferScrolledIncorrectly = false;
    this.terminalWriter.backbufferDirtyCurrentFrame = false;
    this.composeScene(true);
    const rootRegion = this.sceneManager.getRootRegion();
    const cameraY = rootRegion ? this.getCameraY(rootRegion) : 0;
    this.syncCursor(cameraY);
    this.terminalWriter.clear();
    this.terminalWriter.writeLines([...this.backbuffer, ...this.screen]);
    this.updateTrackingMaps(rootRegion, cameraY, true);
    this.terminalWriter.finish();
    this.terminalWriter.flush();
    this.terminalWriter.validateLinesConsistent(this.screen);
    this.logScene();
  }
  async render() {
    const renderTask = this._render();
    this.renderPromise = renderTask;
    try {
      await renderTask;
    } finally {
      if (this.renderPromise === renderTask) {
        this.renderPromise = void 0;
      }
    }
  }
  async flushPendingRender() {
    if (this.terminalWriter.fullRenderTimeout) {
      clearTimeout(this.terminalWriter.fullRenderTimeout);
      this.terminalWriter.fullRenderTimeout = void 0;
      await this.fullRender();
    }
  }
  done() {
    if (this.isRecording) {
      this.stopRecording();
    }
    this.animationController.stop();
    this.terminalWriter.done();
    this.terminalWriter.stdout.write(base_exports.cursorShow);
    if (this.isAlternateBufferEnabled) {
      this.terminalWriter.stdout.write(base_exports.exitAlternativeScreen);
    }
  }
  getLinesUpdated() {
    return this.terminalWriter.getLinesUpdated();
  }
  resetLinesUpdated() {
    this.terminalWriter.resetLinesUpdated();
  }
  clear() {
    this.animationController.stop();
    this.sceneManager.regions.clear();
    this.sceneManager.root = void 0;
    this.sceneManager.regionWasAtEnd.clear();
    this.scrollOptimizer.maxRegionScrollTops.clear();
    this.scrollOptimizer.lastRegionScrollTops.clear();
    this.screen = [];
    this.backbuffer = [];
    this.forceNextRender = false;
    this.cursorPosition = void 0;
    this.primaryTerminalWriter.clear();
    this.alternateTerminalWriter.clear();
    this.terminalWriter.flush();
  }
  serializeCurrentRegions(serializer) {
    const updates = [];
    for (const region of this.sceneManager.regions.values()) {
      const update = {
        id: region.id,
        stickyHeaders: region.stickyHeaders.map((h) => {
          const { node: _node, ...rest } = h;
          return {
            ...rest,
            lines: serializer.serialize(h.lines),
            stuckLines: h.stuckLines ? serializer.serialize(h.stuckLines) : void 0,
            styledOutput: serializer.serialize(h.styledOutput)
          };
        })
      };
      for (const key of regionLayoutProperties) {
        copyRegionProperty(update, region, key);
      }
      if (region.lines.length > 0) {
        update.lines = {
          updates: [
            {
              start: 0,
              end: region.lines.length,
              data: serializer.serialize(region.lines)
            }
          ],
          totalLength: region.lines.length
        };
      }
      updates.push(update);
    }
    return updates;
  }
  async _render() {
    if (clearDebugLogPerFrame) {
      clearDebugLog();
    }
    const rootRegion = this.sceneManager.getRootRegion();
    if (!rootRegion) {
      return;
    }
    if (rootRegion.width === 0) {
      rootRegion.width = this.columns;
    }
    if (rootRegion.height === 0) {
      rootRegion.height = this.rows;
    }
    this.forceNextRender = false;
    if (this.debugRainbowEnabled) {
      this.frameIndex++;
      this.terminalWriter.debugRainbowColor = rainbowColors[this.frameIndex % rainbowColors.length];
    }
    const cameraY = this.getCameraY(rootRegion);
    this.syncCursor(cameraY);
    const scrolledToBackbuffer = /* @__PURE__ */ new Map();
    if (!this.terminalWriter.isFirstRender) {
      const maxPushed = this.scrollOptimizer.maxRegionScrollTops.get(rootRegion.id) ?? 0;
      const linesToScroll = cameraY - maxPushed;
      if (linesToScroll > 0) {
        if (debugWorker) {
          debugLog(`[RENDER-WORKER] Root region ${rootRegion.id} pushing ${linesToScroll} lines to backbuffer (cameraY: ${cameraY}, maxPushed: ${maxPushed})`);
        }
        scrolledToBackbuffer.set(rootRegion.id, linesToScroll);
        this.appendToBackbuffer(maxPushed, linesToScroll);
        this.scrollOptimizer.updateMaxPushed(rootRegion.id, cameraY);
      }
      const compositor = this.createCompositor({
        skipStickyHeaders: true,
        skipScrollbars: false
      });
      for (const region of this.sceneManager.regions.values()) {
        const operations = this.scrollOptimizer.calculateScrollOperations(region, this.rows, this.columns, cameraY, (scrollStart, count, start, end) => {
          const originalScrollTop = region.scrollTop;
          region.scrollTop = scrollStart;
          try {
            const getLines = (skipScrollbars) => {
              const canvas = Canvas.create(this.columns, this.rows + count);
              this.composeNode(this.sceneManager.root, canvas, {
                clip: void 0,
                offsetY: -cameraY
              }, { skipStickyHeaders: true, skipScrollbars });
              const lines = canvas.getLines();
              return start === 0 && end + count === lines.length ? lines : lines.slice(start, end + count);
            };
            const cleanLines = getLines(true);
            if (count > 0 && start === 0) {
              const dirtyLines = getLines(false);
              return [
                ...cleanLines.slice(0, count),
                ...dirtyLines.slice(count)
              ];
            }
            return cleanLines;
          } finally {
            region.scrollTop = originalScrollTop;
          }
        }, (r, s, a) => compositor.calculateActualStuckTopHeight(r, s, a), (r, s, a) => compositor.calculateActualStuckBottomHeight(r, s, a), this.stickyHeadersInBackbuffer);
        for (const op of operations) {
          if (op.scrollToBackbuffer) {
            if (debugWorker) {
              debugLog(`[RENDER-WORKER] Region ${op.regionId} scrolling ${op.linesToScroll} lines to backbuffer`);
            }
            scrolledToBackbuffer.set(op.regionId, (scrolledToBackbuffer.get(op.regionId) ?? 0) + op.linesToScroll);
          }
          this.terminalWriter.scrollLines(op);
          if (op.newMaxPushed !== void 0) {
            this.scrollOptimizer.updateMaxPushed(op.regionId, op.newMaxPushed);
          }
        }
      }
    }
    if (this.terminalWriter.isFirstRender) {
      for (const region of this.sceneManager.regions.values()) {
        if (region.overflowToBackbuffer) {
          this.scrollOptimizer.updateMaxPushed(region.id, region.scrollTop ?? 0);
        }
      }
      if (rootRegion.overflowToBackbuffer) {
        this.scrollOptimizer.updateMaxPushed(rootRegion.id, cameraY);
      }
    }
    this.composeScene(this.terminalWriter.isFirstRender);
    if (this.terminalWriter.isFirstRender) {
      this.terminalWriter.writeLines([...this.backbuffer, ...this.screen]);
    } else {
      for (let row = 0; row < this.rows; row++) {
        this.terminalWriter.syncLine(this.screen[row], row);
      }
    }
    this.terminalWriter.finish();
    this.terminalWriter.flush();
    this.updateTrackingMaps(rootRegion, cameraY);
    if (this.terminalWriter.backbufferDirtyCurrentFrame) {
      this.terminalWriter.backbufferDirty = true;
      if (this.terminalWriter.fullRenderTimeout) {
        clearTimeout(this.terminalWriter.fullRenderTimeout);
      }
      this.terminalWriter.fullRenderTimeout = setTimeout(() => {
        void this.fullRender();
      }, this.backbufferUpdateDelay);
    }
    this.terminalWriter.backbufferDirtyCurrentFrame = false;
    this.logScene(scrolledToBackbuffer);
  }
  tickAnimation() {
    const { hasScrolled, canScrollMore } = this.animationController.updateRegions(this.sceneManager.regions);
    if (hasScrolled) {
      void this.render();
    }
    if (!canScrollMore) {
      if (debugWorker) {
        debugLog(`[RENDER-WORKER] Stopping animation: all targets reached
`);
      }
      this.animationController.stop();
    }
  }
  composeScene(computeBackbuffer) {
    const rootRegion = this.sceneManager.getRootRegion();
    if (!rootRegion) {
      return;
    }
    const cameraY = this.getCameraY(rootRegion);
    this.backbuffer = [];
    if (!this.isAlternateBufferEnabled && computeBackbuffer) {
      const composeToBackbuffer = (node, region, height, offset) => {
        const canvas2 = Canvas.create(this.columns, height);
        const originalScrollTop = region.scrollTop;
        region.scrollTop = offset;
        try {
          this.composeNode(node, canvas2, {
            clip: void 0,
            offsetY: -region.y,
            offsetX: 0,
            overrideHeight: height,
            isExpanded: true
          }, {
            skipStickyHeaders: true,
            skipScrollbars: true
          });
        } finally {
          region.scrollTop = originalScrollTop;
        }
        for (const line of canvas2.getLines()) {
          this.backbuffer.push(this.terminalWriter.clampLine(line.styledChars, this.columns));
        }
      };
      const rootBackbufferHeight = cameraY;
      composeToBackbuffer(this.sceneManager.root, rootRegion, rootBackbufferHeight, 0);
      for (const region of this.sceneManager.regions.values()) {
        if (region.overflowToBackbuffer && region.isScrollable) {
          const scrollTop = region.scrollTop ?? 0;
          const regionBackbufferHeight = scrollTop;
          const node = this.findNodeForRegion(region.id);
          if (node) {
            composeToBackbuffer(node, region, regionBackbufferHeight, 0);
          }
        }
      }
    }
    const canvas = Canvas.create(this.columns, this.rows, this.resized);
    this.composeNode(this.sceneManager.root, canvas, {
      clip: void 0,
      offsetY: -cameraY
    });
    this.screen = canvas.getLines();
    this.resized = false;
  }
  /**
   * Recursively composites a region and its children onto the provided canvas.
   *
   * @param node The hierarchical node to compose.
   * @param canvas The target canvas to draw upon.
   * @param layout Layout and clipping options for the current composition pass.
   * @param layout.clip Optional bounding box to clip rendering.
   * @param layout.offsetY The cumulative Y offset (used for scrolling/camera adjustments).
   * @param layout.offsetX The cumulative X offset (used for scrolling/camera adjustments).
   * @param layout.overrideHeight Optional height to force for the current region, typically used when composing to the backbuffer to capture content that has scrolled out of view.
   * @param layout.isExpanded If true, forces the region to render at its full scroll height rather than its constrained layout height. When composing the backbuffer, this flag is passed down to the specific scrollable descendant that has `overflowToBackbuffer` enabled (typically only one such region should exist), allowing its complete content to be captured instead of just the visible viewport.
   * @param options Additional composition flags.
   * @param options.skipStickyHeaders If true, sticky headers will not be drawn.
   * @param options.skipScrollbars If true, scrollbars will not be drawn.
   */
  composeNode(node, canvas, { clip, offsetY = 0, offsetX = 0, overrideHeight, isExpanded = false }, options) {
    const region = this.sceneManager.getRegion(node.id);
    if (!region)
      return;
    const absX = Math.round(region.x + offsetX);
    const absY = Math.round(region.y + offsetY);
    const inExpandedContext = isExpanded || overrideHeight !== void 0;
    const height = overrideHeight ?? (inExpandedContext && region.isScrollable ? region.scrollHeight ?? 0 : region.height ?? 0);
    if (absY >= canvas.height)
      return;
    if (absY + height < 0 && !this.stickyHeadersInBackbuffer)
      return;
    let myClip = {
      x: absX,
      y: absY,
      w: Math.round(region.width) - (region.marginRight ?? 0),
      h: Math.round(height) - (region.marginBottom ?? 0)
    };
    if (clip) {
      const x1 = Math.max(myClip.x, clip.x);
      const y1 = Math.max(myClip.y, clip.y);
      const x2 = Math.min(myClip.x + myClip.w, clip.x + clip.w);
      const y2 = Math.min(myClip.y + myClip.h, clip.y + clip.h);
      if (x2 <= x1 || y2 <= y1)
        return;
      myClip = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
    }
    const originalScrollTop = region.scrollTop;
    if (inExpandedContext && region.isScrollable && overrideHeight === void 0) {
      region.scrollTop = 0;
    }
    try {
      const compositor = this.createCompositor(options);
      compositor.drawContent(canvas, region, absX, absY, myClip);
      for (const child of node.children) {
        const childRegion = this.sceneManager.getRegion(child.id);
        let childOptions = options;
        if (options && childRegion && childRegion.isScrollable && !childRegion.overflowToBackbuffer) {
          childOptions = {
            ...options,
            skipStickyHeaders: false
          };
        }
        this.composeNode(child, canvas, {
          clip: myClip,
          offsetY: absY - (region.scrollTop ?? 0),
          offsetX: absX - (region.scrollLeft ?? 0),
          isExpanded: inExpandedContext && Boolean(childRegion?.overflowToBackbuffer)
        }, childOptions);
      }
      compositor.drawStickyHeaders(canvas, region, absX, absY, myClip);
      compositor.drawScrollbars(canvas, region, absX, absY, myClip);
    } finally {
      if (inExpandedContext && region.isScrollable && overrideHeight === void 0) {
        region.scrollTop = originalScrollTop;
      }
    }
  }
  createCompositor(options) {
    return new Compositor({
      skipStickyHeaders: options?.skipStickyHeaders,
      skipScrollbars: options?.skipScrollbars,
      stickyHeadersInBackbuffer: this.stickyHeadersInBackbuffer,
      animatedScroll: this.animatedScroll,
      targetScrollTops: this.animationController.allTargetScrollTops,
      regionWasAtEnd: this.sceneManager.regionWasAtEnd,
      canvasHeight: this.rows
    });
  }
  getCameraY(rootRegion) {
    return Math.max(0, rootRegion.height - this.rows);
  }
  syncCursor(cameraY) {
    let cursorRow = -1;
    let cursorCol = -1;
    if (this.cursorPosition) {
      const row = this.cursorPosition.row - cameraY;
      if (row >= 0 && row < this.rows) {
        cursorRow = row;
        cursorCol = this.cursorPosition.col;
      }
    }
    this.terminalWriter.setTargetCursorPosition(cursorRow, cursorCol);
  }
  appendToBackbuffer(start, count) {
    const rootNode = this.sceneManager.root;
    if (!rootNode)
      return;
    const canvas = Canvas.create(this.columns, count);
    this.composeNode(rootNode, canvas, { clip: void 0, offsetY: -start }, {
      skipStickyHeaders: true,
      skipScrollbars: true
    });
    const linesScrollingOut = canvas.getLines().map((line) => this.terminalWriter.clampLine(line.styledChars, this.columns));
    this.terminalWriter.appendLinesBackbuffer(linesScrollingOut);
  }
  updateTrackingMaps(rootRegion, cameraY, reset = false) {
    if (rootRegion) {
      if (reset) {
        this.scrollOptimizer.setMaxPushed(rootRegion.id, cameraY);
      } else {
        this.scrollOptimizer.updateMaxPushed(rootRegion.id, cameraY);
      }
    }
    for (const region of this.sceneManager.regions.values()) {
      if (region.isScrollable) {
        this.scrollOptimizer.lastRegionScrollTops.set(region.id, region.scrollTop ?? 0);
        if (region.overflowToBackbuffer) {
          if (reset) {
            this.scrollOptimizer.setMaxPushed(region.id, region.scrollTop ?? 0);
          } else {
            this.scrollOptimizer.updateMaxPushed(region.id, region.scrollTop ?? 0);
          }
        }
      }
    }
  }
  findNodeForRegion(id) {
    if (!this.sceneManager.root)
      return void 0;
    const visit = (node) => {
      if (node.id === id)
        return node;
      for (const child of node.children) {
        const found = visit(child);
        if (found)
          return found;
      }
      return void 0;
    };
    return visit(this.sceneManager.root);
  }
  logScene(scrolledToBackbuffer) {
    if (!debugWorker) {
      return;
    }
    const rootNode = this.sceneManager.root;
    if (!rootNode) {
      return;
    }
    const rootRegion = this.sceneManager.getRootRegion();
    const cameraY = rootRegion ? this.getCameraY(rootRegion) : 0;
    debugLog("=".repeat(80));
    debugLog(`FRAME START (Index: ${this.frameIndex})`);
    debugLog("=".repeat(80));
    const traverse = (node, depth, offsetX, offsetY, clip) => {
      const region = this.sceneManager.getRegion(node.id);
      if (!region) {
        return;
      }
      const absX = Math.round(region.x + offsetX);
      const absY = Math.round(region.y + offsetY);
      const width = Math.round(region.width);
      const height = Math.round(region.height);
      let myClip = {
        x: absX,
        y: absY,
        w: width,
        h: height
      };
      if (clip) {
        const x1 = Math.max(myClip.x, clip.x);
        const y1 = Math.max(myClip.y, clip.y);
        const x2 = Math.min(myClip.x + myClip.w, clip.x + clip.w);
        const y2 = Math.min(myClip.y + myClip.h, clip.y + clip.h);
        myClip = x2 > x1 && y2 > y1 ? { x: x1, y: y1, w: x2 - x1, h: y2 - y1 } : { x: 0, y: 0, w: 0, h: 0 };
      }
      const indent = "  ".repeat(depth);
      const isStatic = region.node?.nodeName === "ink-static-render";
      debugLog(`${indent}Region: ${region.id} ${isStatic ? "(STATIC)" : ""}`);
      debugLog(`${indent}  Bounds: x=${absX}, y=${absY}, w=${width}, h=${height}`);
      debugLog(`${indent}  Scroll: top=${region.scrollTop ?? 0}, left=${region.scrollLeft ?? 0}, height=${region.scrollHeight ?? 0}, width=${region.scrollWidth ?? 0}`);
      const linesPushed = this.scrollOptimizer.maxRegionScrollTops.get(region.id) ?? 0;
      const justScrolled = scrolledToBackbuffer?.get(region.id) ?? 0;
      debugLog(`${indent}  Backbuffer: enabled=${region.overflowToBackbuffer ?? false}, linesPushed=${linesPushed}${justScrolled > 0 ? `, JUST_SCROLLED=${justScrolled}` : ""}`);
      debugLog(`${indent}  Clip: x=${myClip.x}, y=${myClip.y}, w=${myClip.w}, h=${myClip.h}`);
      if (region.lines.length > 0) {
        debugLog(`${indent}  Content:`);
        for (const line of region.lines) {
          const plainText = line.getText().trimEnd();
          if (plainText) {
            debugLog(`${indent}    ${plainText}`);
          }
        }
      }
      if (region.stickyHeaders.length > 0) {
        debugLog(`${indent}  Sticky Headers:`);
        for (const header of region.stickyHeaders) {
          const scrollTop = region.scrollTop ?? 0;
          const isStuckState = header.type === "bottom" ? Math.round(header.naturalRow - scrollTop + header.lines.length) >= Math.round(header.y + (header.stuckLines ?? header.lines).length) : Math.round(header.naturalRow - scrollTop) <= Math.round(header.y);
          let isStuck = isStuckState;
          if (isStuck && header.type === "top") {
            isStuck = this.stickyHeadersInBackbuffer || absY > 0;
          }
          debugLog(`${indent}    Header nodeID: ${header.nodeId}, type: ${header.type}, isStuckOnly: ${header.isStuckOnly}, IS_STUCK: ${isStuck}`);
          debugLog(`${indent}    Range: ${header.startRow}-${header.endRow}, StuckPos: y=${header.y}, NaturalRow: ${header.naturalRow}`);
          const linesToLog = isStuck ? header.stuckLines ?? header.lines : header.lines;
          debugLog(`${indent}    Header Content (${isStuck ? "STUCK" : "NATURAL"}):`);
          for (const line of linesToLog) {
            const plainText = line.getText().trimEnd();
            if (plainText) {
              debugLog(`${indent}      ${plainText}`);
            }
          }
        }
      }
      for (const child of node.children) {
        traverse(child, depth + 1, absX - (region.scrollLeft ?? 0), absY - (region.scrollTop ?? 0), myClip);
      }
    };
    traverse(rootNode, 0, 0, -cameraY, {
      x: 0,
      y: 0,
      w: this.columns,
      h: this.rows
    });
    debugLog("=".repeat(80));
    debugLog("FRAME END");
    debugLog("=".repeat(80));
  }
};

// node_modules/ink/build/worker/worker-entry.js
var buffer;
var main = () => {
  process7.on("message", async (message) => {
    switch (message.type) {
      case "init": {
        const columns = process7.stdout.columns || message.columns;
        const rows = process7.stdout.rows || message.rows;
        buffer = new TerminalBufferWorker(columns, rows, {
          debugRainbowEnabled: message.debugRainbowEnabled,
          isAlternateBufferEnabled: message.isAlternateBufferEnabled,
          stickyHeadersInBackbuffer: message.stickyHeadersInBackbuffer,
          animatedScroll: message.animatedScroll,
          animationInterval: message.animationInterval,
          backbufferUpdateDelay: message.backbufferUpdateDelay,
          maxScrollbackLength: message.maxScrollbackLength,
          forceScrollToBottomOnBackbufferRefresh: message.forceScrollToBottomOnBackbufferRefresh
        });
        break;
      }
      case "updateOptions": {
        if (buffer) {
          buffer.updateOptions(message.options);
        }
        break;
      }
      case "edits": {
        if (buffer) {
          buffer.update(message.tree, message.updates, message.cursorPosition);
        }
        break;
      }
      case "fullRender": {
        if (buffer) {
          void buffer.fullRender();
        }
        break;
      }
      case "render": {
        if (buffer) {
          await buffer.render();
          process7.send?.({ type: "renderDone" });
        }
        break;
      }
      case "done": {
        if (buffer) {
          buffer.done();
          process7.send?.({ type: "doneConfirmed" });
        }
        break;
      }
      case "getLinesUpdated": {
        if (buffer) {
          process7.send?.({
            type: "linesUpdated",
            count: buffer.getLinesUpdated()
          });
        }
        break;
      }
      case "resetLinesUpdated": {
        if (buffer) {
          buffer.resetLinesUpdated();
        }
        break;
      }
      case "clear": {
        if (buffer) {
          buffer.clear();
          process7.send?.({ type: "clearDone" });
        }
        break;
      }
      case "resize": {
        if (buffer) {
          buffer.resize(message.columns, message.rows);
        }
        break;
      }
      case "dumpCurrentFrame": {
        if (buffer) {
          buffer.dumpCurrentFrame(message.filename);
        }
        break;
      }
      case "startRecording": {
        if (buffer) {
          buffer.startRecording(message.filename);
        }
        break;
      }
      case "stopRecording": {
        if (buffer) {
          buffer.stopRecording();
        }
        break;
      }
      case "waitForIdle": {
        if (buffer) {
          await buffer.waitForIdle();
          process7.send?.({ type: "idle" });
        }
        break;
      }
      default: {
        break;
      }
    }
  });
  process7.stdout.on("resize", () => {
    if (buffer && process7.stdout.columns && process7.stdout.rows) {
      buffer.resize(process7.stdout.columns, process7.stdout.rows);
    }
  });
};
if (process7.env["INK_WORKER"] === "true") {
  main();
}
/*! Bundled license information:

ink/build/styled-line.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/scroll.js:
  (**
   * @license
   * Copyright 2025 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/text-wrap.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/layout.js:
  (**
   * @license
   * Copyright 2025 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/replay.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/ansi-utils.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/platform.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/terminal-writer.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/canvas.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/scene-manager.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/animation-controller.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/compositor.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/scroll-optimizer.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/render-worker.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)

ink/build/worker/worker-entry.js:
  (**
   * @license
   * Copyright 2026 Google LLC
   * SPDX-License-Identifier: Apache-2.0
   *)
*/
