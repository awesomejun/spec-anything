// Clean-room 2048 Tile module built from 01-12 specification
function Tile(position, value) {
  this.x = position.x;
  this.y = position.y;
  this.value = value || 2;
  this.previousPosition = null;
  this.mergedFrom = null;
}
Tile.prototype.savePosition = function () {
  this.previousPosition = { x: this.x, y: this.y };
};
Tile.prototype.updatePosition = function (pos) {
  this.x = pos.x;
  this.y = pos.y;
};
Tile.prototype.serialize = function () {
  return { position: { x: this.x, y: this.y }, value: this.value };
};
