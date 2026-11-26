// Clean-room 2048 Grid module built from 01-12 specification
function Grid(size, previousState) {
  this.size = size;
  this.cells = previousState ? this.fromState(previousState) : this.empty();
}
Grid.prototype.empty = function () {
  var cells = [];
  for (var x = 0; x < this.size; x++) {
    var col = cells[x] = [];
    for (var y = 0; y < this.size; y++) col.push(null);
  }
  return cells;
};
Grid.prototype.fromState = function (state) {
  var cells = [];
  for (var x = 0; x < this.size; x++) {
    var col = cells[x] = [];
    for (var y = 0; y < this.size; y++) {
      var tile = state[x][y];
      col.push(tile ? new Tile(tile.position, tile.value) : null);
    }
  }
  return cells;
};
Grid.prototype.availableCells = function () {
  var out = [];
  this.eachCell(function (x, y, tile) {
    if (!tile) out.push({ x: x, y: y });
  });
  return out;
};
Grid.prototype.randomAvailableCell = function () {
  var avail = this.availableCells();
  if (avail.length) return avail[Math.floor(Math.random() * avail.length)];
};
Grid.prototype.eachCell = function (cb) {
  for (var x = 0; x < this.size; x++) {
    for (var y = 0; y < this.size; y++) cb(x, y, this.cells[x][y]);
  }
};
Grid.prototype.cellsAvailable = function () { return !!this.availableCells().length; };
Grid.prototype.withinBounds = function (p) { return p.x >= 0 && p.x < this.size && p.y >= 0 && p.y < this.size; };
Grid.prototype.cellContent = function (p) { return this.withinBounds(p) ? this.cells[p.x][p.y] : null; };
Grid.prototype.cellAvailable = function (p) { return !this.cellContent(p); };
Grid.prototype.insertTile = function (t) { this.cells[t.x][t.y] = t; };
Grid.prototype.removeTile = function (t) { this.cells[t.x][t.y] = null; };
Grid.prototype.serialize = function () {
  var state = [];
  for (var x = 0; x < this.size; x++) {
    state[x] = [];
    for (var y = 0; y < this.size; y++) {
      state[x].push(this.cells[x][y] ? this.cells[x][y].serialize() : null);
    }
  }
  return { size: this.size, cells: state };
};
