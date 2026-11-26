// Clean-room 2048 LocalStorageManager built from 01-12 specification
function LocalStorageManager() {
  this.bestScoreKey = "bestScore";
  this.gameStateKey = "gameState";
  this.storage = window.localStorage;
}
LocalStorageManager.prototype.getBestScore = function () {
  return this.storage.getItem(this.bestScoreKey) || 0;
};
LocalStorageManager.prototype.setBestScore = function (score) {
  this.storage.setItem(this.bestScoreKey, score);
};
LocalStorageManager.prototype.getGameState = function () {
  var raw = this.storage.getItem(this.gameStateKey);
  return raw ? JSON.parse(raw) : null;
};
LocalStorageManager.prototype.setGameState = function (state) {
  this.storage.setItem(this.gameStateKey, JSON.stringify(state));
};
LocalStorageManager.prototype.clearGameState = function () {
  this.storage.removeItem(this.gameStateKey);
};
