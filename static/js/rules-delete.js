document.addEventListener('DOMContentLoaded', function () {
  console.log('rules-delete.js loaded');
  var modal = document.getElementById('delete-modal');
  var cancelBtn = document.getElementById('delete-cancel-btn');
  var confirmBtn = document.getElementById('delete-confirm-btn');
  var currentRuleId = null;

  // Attach click listeners to all delete buttons with data-rule-id
  var deleteBtns = document.querySelectorAll('.delete-btn[data-rule-id]');
  deleteBtns.forEach(function(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      currentRuleId = btn.getAttribute('data-rule-id');
      modal.style.display = 'flex';
    });
  });

  // Cancel closes modal
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function () {
      modal.style.display = 'none';
      currentRuleId = null;
    });
  }

  // Confirm submits the hidden form
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function () {
      if (currentRuleId) {
        var form = document.getElementById('delete-form-' + currentRuleId);
        if (form) form.submit();
      }
      modal.style.display = 'none';
      currentRuleId = null;
    });
  }

  // Optional: close modal on background click
  modal.addEventListener('click', function (e) {
    if (e.target === modal) {
      modal.style.display = 'none';
      currentRuleId = null;
    }
  });
});
