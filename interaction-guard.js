/* Accessibility and pointer guard for interactive cards/ticker. */
(function(){'use strict';document.addEventListener('keydown',e=>{if(e.target.closest('#ticker')&&['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();document.getElementById('ticker')?.classList.add('paused')}});})();
