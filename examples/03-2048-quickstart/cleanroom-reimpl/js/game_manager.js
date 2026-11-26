// Clean-room 2048 GameManager built strictly from 01-12 & 06-engine.jsonl specification
function GameManager(size, InputManager, Actuator, StorageManager) {
  this.size = size;
  this.inputManager = new InputManager();
  this.storageManager = new StorageManager();
  this.actuator = new Actuator();
  this.startTiles = 2;
  this.inputManager.on("move", this.move.bind(this));
  this.inputManager.on("restart", this.restart.bind(this));
  this.inputManager.on("keepPlaying", this.keepPlaying.bind(this));
  this.setup();
}
GameManager.prototype.restart = function () {
  this.storageManager.clearGameState();
  this.actuator.continueGame();
  this.setup();
};
GameManager.prototype.keepPlaying = function () {
  this.keepPlaying = true;
  this.actuator.continueGame();
};
GameManager.prototype.isGameTerminated = function () {
  return this.over || (this.won && !this.keepPlaying);
};
GameManager.prototype.setup = function () {
  var prev = this.storageManager.getGameState();
  if (prev) {
    this.grid = new Grid(prev.grid.size, prev.grid.cells);
    this.score = prev.score;
    this.over = prev.over;
    this.won = prev.won;
    this.keepPlaying = prev.keepPlaying;
  } else {
    this.grid = new Grid(this.size);
    this.score = 0;
    this.over = false;
    this.won = false;
    this.keepPlaying = false;
    for (var i = 0; i < this.startTiles; i++) this.addRandomTile();
  }
  this.actuate();
};
GameManager.prototype.addRandomTile = function () {
  if (this.grid.cellsAvailable()) {
    var val = Math.random() < 0.9 ? 2 : 4;
    this.grid.insertTile(new Tile(this.grid.randomAvailableCell(), val));
  }
};
GameManager.prototype.actuate = function () {
  if (this.storageManager.getBestScore() < this.score) {
    this.storageManager.setBestScore(this.score);
  }
  if (this.over) this.storageManager.clearGameState();
  else this.storageManager.setGameState(this.serialize());
  this.actuator.actuate(this.grid, {
    score: this.score,
    over: this.over,
    won: this.won,
    bestScore: this.storageManager.getBestScore(),
    terminated: this.isGameTerminated()
  });
};
GameManager.prototype.serialize = function () {
  return {
    grid: this.grid.serialize(),
    score: this.score,
    over: this.over,
    won: this.won,
    keepPlaying: this.keepPlaying
  };
};
GameManager.prototype.prepareTiles = function () {
  this.grid.eachCell(function (x, y, tile) {
    if (tile) { tile.mergedFrom = null; tile.savePosition(); }
  });
};
GameManager.prototype.moveTile = function (tile, cell) {
  this.grid.cells[tile.x][tile.y] = null;
  this.grid.cells[cell.x][cell.y] = tile;
  tile.updatePosition(cell);
};
GameManager.prototype.getVector = function (dir) {
  return { 0: { x: 0, y: -1 }, 1: { x: 1, y: 0 }, 2: { x: 0, y: 1 }, 3: { x: -1, y: 0 } }[dir];
};
GameManager.prototype.buildTraversals = function (v) {
  var t = { x: [], y: [] };
  for (var p = 0; p < this.size; p++) { t.x.push(p); t.y.push(p); }
  if (v.x === 1) t.x.reverse();
  if (v.y === 1) t.y.reverse();
  return t;
};
GameManager.prototype.findFarthestPosition = function (cell, v) {
  var prev;
  do { prev = cell; cell = { x: prev.x + v.x, y: prev.y + v.y }; }
  while (this.grid.withinBounds(cell) && this.grid.cellAvailable(cell));
  return { farthest: prev, next: cell };
};
GameManager.prototype.positionsEqual = function (a, b) { return a.x === b.x && a.y === b.y; };
GameManager.prototype.movesAvailable = function () { return this.grid.cellsAvailable() || this.tileMatchesAvailable(); };
GameManager.prototype.tileMatchesAvailable = function () {
  for (var x = 0; x < this.size; x++) {
    for (var y = 0; y < this.size; y++) {
      var t = this.grid.cellContent({ x: x, y: y });
      if (!t) continue;
      for (var d = 0; d < 4; d++) {
        var v = this.getVector(d);
        var o = this.grid.cellContent({ x: x + v.x, y: y + v.y });
        if (o && o.value === t.value) return true;
      }
    }
  }
  return false;
};
GameManager.prototype.move = function (direction) {
  var self = this;
  if (this.isGameTerminated()) return;
  var vector = this.getVector(direction);
  var traversals = this.buildTraversals(vector);
  var moved = false;
  this.prepareTiles();
  traversals.x.forEach(function (x) {
    traversals.y.forEach(function (y) {
      var cell = { x: x, y: y };
      var tile = self.grid.cellContent(cell);
      if (tile) {
        var pos = self.findFarthestPosition(cell, vector);
        var next = self.grid.cellContent(pos.next);
        if (next && next.value === tile.value && !next.mergedFrom) {
          var merged = new Tile(pos.next, tile.value * 2);
          merged.mergedFrom = [tile, next];
          self.grid.insertTile(merged);
          self.grid.removeTile(tile);
          tile.updatePosition(pos.next);
          self.score += merged.value;
          if (merged.value === 2048) self.won = true;
        } else {
          self.moveTile(tile, pos.farthest);
        }
        if (!self.positionsEqual(cell, tile)) moved = true;
      }
    });
  });
  if (moved) {
    this.addRandomTile();
    if (!this.movesAvailable()) this.over = true;
    this.actuate();
  }
};
