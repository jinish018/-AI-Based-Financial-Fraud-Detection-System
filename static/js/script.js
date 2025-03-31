document.addEventListener('DOMContentLoaded', function () {
  // Navigation between dashboard sections
  const navLinks = document.querySelectorAll('.sidebar a[data-section]');
  navLinks.forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      const targetSection = this.getAttribute('data-section');

      // Hide all sections
      document.querySelectorAll('.dashboard-section').forEach(section => {
        section.classList.remove('active');
      });

      // Show target section
      document.getElementById(targetSection).classList.add('active');

      // Update active nav link
      document.querySelectorAll('.sidebar li').forEach(item => {
        item.classList.remove('active');
      });
      this.parentElement.classList.add('active');
    });
  });

  // Transaction form toggle
  const addTransactionBtn = document.getElementById('add-transaction-btn');
  const transactionFormContainer = document.getElementById('transaction-form-container');
  const cancelTransactionBtn = document.getElementById('cancel-transaction');

  if (addTransactionBtn && transactionFormContainer && cancelTransactionBtn) {
    addTransactionBtn.addEventListener('click', function () {
      transactionFormContainer.classList.remove('hidden');
    });

    cancelTransactionBtn.addEventListener('click', function () {
      transactionFormContainer.classList.add('hidden');
      document.getElementById('transaction-form').reset();
    });
  }

  // Transaction form submission
  const transactionForm = document.getElementById('transaction-form');
  if (transactionForm) {
    transactionForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const formData = new FormData(this);

      fetch('/add_transaction', {
        method: 'POST',
        body: formData
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Hide form and reset
            transactionFormContainer.classList.add('hidden');
            transactionForm.reset();

            // Refresh transactions
            loadTransactions();

            // Show success message
            alert('Transaction added successfully');

            // If transaction is fraudulent, show details
            if (data.transaction.is_fraud) {
              showTransactionDetails(data.transaction);
            }
          } else {
            alert('Error: ' + data.error);
          }
        })
        .catch(error => {
          console.error('Error:', error);
          alert('An error occurred while submitting the transaction');
        });
    });
  }

  // Load transactions
  function loadTransactions() {
    const transactionsBody = document.getElementById('transactions-body');
    if (!transactionsBody) return;

    transactionsBody.innerHTML = '<tr><td colspan="7" class="loading-message">Loading transactions...</td></tr>';

    fetch('/get_transactions')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          if (data.transactions.length === 0) {
            transactionsBody.innerHTML = '<tr><td colspan="7" class="loading-message">No transactions found</td></tr>';
            return;
          }

          transactionsBody.innerHTML = '';

          data.transactions.forEach(transaction => {
            const row = document.createElement('tr');
            if (transaction.is_fraud) {
              row.classList.add('fraud-transaction');
            }

            // Format date
            const date = new Date(transaction.timestamp);
            const formattedDate = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;

            // Format amount
            const formattedAmount = new Intl.NumberFormat('en-US', {
              style: 'currency',
              currency: 'USD'
            }).format(transaction.amount);

            // Status badge
            const statusBadge = transaction.is_fraud
              ? '<span class="transaction-status status-fraud">Suspicious</span>'
              : '<span class="transaction-status status-legitimate">Legitimate</span>';

            row.innerHTML = `
                          <td>${formattedDate}</td>
                          <td>${formattedAmount}</td>
                          <td>${transaction.merchant}</td>
                          <td>${transaction.category}</td>
                          <td>${transaction.location}</td>
                          <td>${statusBadge}</td>
                          <td>
                              <button class="btn btn-small view-details" data-id="${transaction.id}">Details</button>
                          </td>
                      `;

            transactionsBody.appendChild(row);
          });

          // Add event listeners to view details buttons
          document.querySelectorAll('.view-details').forEach(button => {
            button.addEventListener('click', function () {
              const transactionId = this.getAttribute('data-id');
              const transaction = data.transactions.find(t => t.id === transactionId);
              if (transaction) {
                showTransactionDetails(transaction);
              }
            });
          });

          // Update admin stats if available
          updateAdminStats(data.transactions);
        } else {
          transactionsBody.innerHTML = `<tr><td colspan="7" class="loading-message">Error: ${data.error}</td></tr>`;
        }
      })
      .catch(error => {
        console.error('Error:', error);
        transactionsBody.innerHTML = '<tr><td colspan="7" class="loading-message">An error occurred while loading transactions</td></tr>';
      });
  }

  // Show transaction details in modal
  function showTransactionDetails(transaction) {
    const modal = document.getElementById('transaction-details-modal');
    const content = document.getElementById('transaction-details-content');

    if (!modal || !content) return;

    // Format date
    const date = new Date(transaction.timestamp);
    const formattedDate = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;

    // Format amount
    const formattedAmount = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(transaction.amount);

    // Status badge
    const statusBadge = transaction.is_fraud
      ? '<span class="transaction-status status-fraud">Suspicious</span>'
      : '<span class="transaction-status status-legitimate">Legitimate</span>';

    // Fraud score visualization
    let scoreBar = '';
    if (transaction.fraud_score !== undefined) {
      const scorePercentage = Math.round(transaction.fraud_score * 100);
      const scoreColor = transaction.is_fraud ? 'var(--accent-color)' : 'var(--success-color)';

      scoreBar = `
              <div class="fraud-score-container">
                  <div class="fraud-score-label">Fraud Score: ${scorePercentage}%</div>
                  <div class="fraud-score-bar">
                      <div class="fraud-score-fill" style="width: ${scorePercentage}%; background-color: ${scoreColor};"></div>
                  </div>
              </div>
          `;
    }

    // Fraud reason
    let fraudReason = '';
    if (transaction.is_fraud && transaction.fraud_reason) {
      fraudReason = `
              <div class="fraud-reason">
                  <h4>Fraud Detection Insights:</h4>
                  <p>${transaction.fraud_reason}</p>
              </div>
          `;
    }

    content.innerHTML = `
          <div class="transaction-details">
              <div class="transaction-header">
                  <h3>${transaction.merchant}</h3>
                  <div>${statusBadge}</div>
              </div>
              
              <div class="transaction-info">
                  <div class="info-group">
                      <div class="info-label">Transaction ID:</div>
                      <div class="info-value">${transaction.id}</div>
                  </div>
                  <div class="info-group">
                      <div class="info-label">Date & Time:</div>
                      <div class="info-value">${formattedDate}</div>
                  </div>
                  <div class="info-group">
                      <div class="info-label">Amount:</div>
                      <div class="info-value">${formattedAmount}</div>
                  </div>
                  <div class="info-group">
                      <div class="info-label">Category:</div>
                      <div class="info-value">${transaction.category}</div>
                  </div>
                  <div class="info-group">
                      <div class="info-label">Location:</div>
                      <div class="info-value">${transaction.location}</div>
                  </div>
                  <div class="info-group">
                      <div class="info-label">Card Type:</div>
                      <div class="info-value">${transaction.card_type}</div>
                  </div>
                  <div class="info-group">
                      <div class="info-label">Description:</div>
                      <div class="info-value">${transaction.description || 'N/A'}</div>
                  </div>
              </div>
              
              ${scoreBar}
              ${fraudReason}
          </div>
      `;

    // Add custom styles for the details modal
    const style = document.createElement('style');
    style.textContent = `
          .transaction-details {
              padding: 1rem 0;
          }
          .transaction-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 1.5rem;
              padding-bottom: 1rem;
              border-bottom: 1px solid var(--border-color);
          }
          .info-group {
              display: flex;
              margin-bottom: 0.75rem;
          }
          .info-label {
              width: 120px;
              font-weight: 600;
          }
          .info-value {
              flex: 1;
          }
          .fraud-score-container {
              margin-top: 1.5rem;
              padding-top: 1.5rem;
              border-top: 1px solid var(--border-color);
          }
          .fraud-score-label {
              margin-bottom: 0.5rem;
              font-weight: 600;
          }
          .fraud-score-bar {
              height: 10px;
              background-color: #eee;
              border-radius: 5px;
              overflow: hidden;
          }
          .fraud-score-fill {
              height: 100%;
              border-radius: 5px;
          }
          .fraud-reason {
              margin-top: 1.5rem;
              padding: 1rem;
              background-color: rgba(231, 76, 60, 0.1);
              border-radius: 4px;
          }
          .fraud-reason h4 {
              color: var(--accent-color);
              margin-bottom: 0.5rem;
          }
      `;
    document.head.appendChild(style);

    // Show modal
    modal.style.display = 'block';

    // Close modal when clicking on X
    const closeBtn = modal.querySelector('.close-modal');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        modal.style.display = 'none';
      });
    }

    // Close modal when clicking outside
    window.addEventListener('click', function (event) {
      if (event.target === modal) {
        modal.style.display = 'none';
      }
    });
  }

  // Update admin stats
  function updateAdminStats(transactions) {
    const totalTransactionsEl = document.getElementById('total-transactions');
    const fraudTransactionsEl = document.getElementById('fraud-transactions');
    const fraudPercentageEl = document.getElementById('fraud-percentage');

    if (!totalTransactionsEl || !fraudTransactionsEl || !fraudPercentageEl) return;

    const totalCount = transactions.length;
    const fraudCount = transactions.filter(t => t.is_fraud).length;
    const fraudPercentage = totalCount > 0 ? ((fraudCount / totalCount) * 100).toFixed(2) : 0;

    totalTransactionsEl.querySelector('.stat-value').textContent = totalCount;
    fraudTransactionsEl.querySelector('.stat-value').textContent = fraudCount;
    fraudPercentageEl.querySelector('.stat-value').textContent = `${fraudPercentage}%`;
  }

  // Transaction search and filtering
  const searchInput = document.getElementById('search-transactions');
  const filterFraud = document.getElementById('filter-fraud');

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      filterTransactions();
    });
  }

  if (filterFraud) {
    filterFraud.addEventListener('change', function () {
      filterTransactions();
    });
  }

  function filterTransactions() {
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const fraudFilter = filterFraud ? filterFraud.value : 'all';

    const rows = document.querySelectorAll('#transactions-body tr');

    rows.forEach(row => {
      if (row.querySelector('.loading-message')) return;

      const text = row.textContent.toLowerCase();
      const isFraud = row.classList.contains('fraud-transaction');

      let showRow = text.includes(searchTerm);

      if (fraudFilter === 'fraud') {
        showRow = showRow && isFraud;
      } else if (fraudFilter === 'legitimate') {
        showRow = showRow && !isFraud;
      }

      row.style.display = showRow ? '' : 'none';
    });
  }

  // Load transactions on page load
  if (document.getElementById('transactions-body')) {
    loadTransactions();
  }
});

// Add custom styles for transaction rows
document.addEventListener('DOMContentLoaded', function () {
  const style = document.createElement('style');
  style.textContent = `
      .fraud-transaction {
          background-color: rgba(231, 76, 60, 0.05);
      }
      .fraud-transaction:hover {
          background-color: rgba(231, 76, 60, 0.1);
      }
  `;
  document.head.appendChild(style);
});