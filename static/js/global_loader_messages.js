// Motivational and playful loading messages for Chase The Zones
window.CTZ_LOADING_MESSAGES = [
  "Chasing your best self…",
  "Warming up your zones…",
  "Getting in the zone…",
  "Fueling your motivation…",
  "Syncing your energy…",
  "Prepping your next achievement…",
  "Lacing up your sneakers…",
  "Setting the pace…",
  "Unleashing your potential…",
  "Crunching the numbers…",
  "Almost ready to go!",
  "Loading your journey…",
  "Powering up your progress…"
];

window.setRandomLoaderMessage = function() {
  var messages = window.CTZ_LOADING_MESSAGES;
  var msg = messages[Math.floor(Math.random() * messages.length)];
  var el = document.getElementById('global-loader-message');
  if (el) el.textContent = msg;
};

document.addEventListener('DOMContentLoaded', function() {
  setRandomLoaderMessage();
});
