(function () {
  const form = document.getElementById('filterForm');
  const statusEl = document.getElementById('status');

  function setStatus(msg, isError = false) {
    statusEl.textContent = msg;
    statusEl.style.color = isError ? '#fca5a5' : '#9ca3af';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    setStatus('Collecting data...');

    const loginNumber = document.getElementById('loginNumber').value.trim();
    const symbol = document.getElementById('symbol').value.trim();
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;

    try {
      const result = await API.collect({ loginNumber, symbol, startTime, endTime });
      setStatus('Success. Redirecting to tables view...');
      // Optionally store available table names
      if (result && result.available_tables) {
        localStorage.setItem('available_tables', JSON.stringify(result.available_tables));
      }
      window.location.href = '/frontend/table_view/index.html';
    } catch (err) {
      setStatus(err.message || 'An error occurred.', true);
    }
  });
})();
