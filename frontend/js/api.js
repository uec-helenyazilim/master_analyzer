const API = {
  async collect({ loginNumber, symbol, startTime, endTime }) {
    const payload = {
      login_number: loginNumber ? Number(loginNumber) : null,
      symbol: symbol || null,
      start_time: startTime || null,
      end_time: endTime || null,
    };

    const res = await fetch('/api/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error || `Collect failed: ${res.status}`);
    }

    return res.json();
  },

  async getTables() {
    const res = await fetch('/api/tables');
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error || `Tables fetch failed: ${res.status}`);
    }
    return res.json();
  },
};
