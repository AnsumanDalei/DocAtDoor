document.querySelectorAll('.visit-request-form, .reschedule-visit-form').forEach(function (form) {
  var dateField = form.querySelector('.visit-date');
  var timeField = form.querySelector('.visit-time');
  var datetimeField = form.querySelector('.visit-datetime');
  var reviewButton = form.querySelector('.review-request-button');
  var confirmButton = form.querySelector('.confirm-request-button');
  var editButton = form.querySelector('.edit-request-button');
  var entry = form.querySelector('.booking-entry');
  var review = form.querySelector('.booking-review');
  var status = form.querySelector('.slot-status');
  var progressSteps = form.querySelectorAll('.booking-progress li');
  if (!dateField || !timeField || !datetimeField) return;

  function setProgress(activeIndex) {
    progressSteps.forEach(function (step, index) {
      step.classList.toggle('is-current', index === activeIndex);
      step.classList.toggle('is-complete', index < activeIndex);
      if (index === activeIndex) step.setAttribute('aria-current', 'step');
      else step.removeAttribute('aria-current');
    });
  }

  function resetReview() {
    if (!entry || !review) return;
    entry.hidden = false;
    review.hidden = true;
    if (reviewButton) reviewButton.hidden = false;
    if (confirmButton) confirmButton.hidden = true;
  }

  dateField.addEventListener('change', async function () {
    resetReview();
    if (progressSteps.length) setProgress(1);
    timeField.disabled = true;
    timeField.innerHTML = '<option value="">Loading available times…</option>';
    datetimeField.value = '';
    if (reviewButton) reviewButton.disabled = true;
    var submitButton = form.querySelector('.request-submit');
    if (submitButton) submitButton.disabled = true;
    if (!dateField.value) {
      timeField.innerHTML = '<option value="">Choose a date first</option>';
      if (status) status.textContent = 'Choose a date to see available visits.';
      return;
    }
    try {
      var url = new URL(form.dataset.slotsUrl, window.location.origin);
      url.searchParams.set('date', dateField.value);
      var response = await fetch(url, {headers: {'Accept': 'application/json'}});
      var data = await response.json();
      timeField.innerHTML = '';
      if (!response.ok) throw new Error(data.error || 'Times could not be loaded.');
      if (!data.slots.length) {
        timeField.innerHTML = '<option value="">No times available</option>';
        if (status) status.textContent = 'No visit times are available on this date. Try another day.';
        return;
      }
      timeField.add(new Option('Select a time', ''));
      data.slots.forEach(function (slot) { timeField.add(new Option(slot.label, slot.value)); });
      timeField.disabled = false;
      if (status) status.textContent = data.slots.length + ' visit time' + (data.slots.length === 1 ? '' : 's') + ' available.';
    } catch (error) {
      timeField.innerHTML = '<option value="">Times unavailable</option>';
      if (status) status.textContent = error.message || 'Could not load available times. Please try again.';
    }
  });

  timeField.addEventListener('change', function () {
    datetimeField.value = timeField.value;
    if (progressSteps.length && timeField.value) setProgress(2);
    if (reviewButton) reviewButton.disabled = !timeField.value;
    var submitButton = form.querySelector('.request-submit');
    if (submitButton) submitButton.disabled = !timeField.value;
  });

  if (reviewButton) reviewButton.addEventListener('click', function () {
    if (!form.reportValidity()) return;
    var values = {
      doctor: form.dataset.doctorName || '',
      when: '',
      fee: form.dataset.fee || 'Fee shared after request',
      reason: form.querySelector('[name="symptom_description"]').value.trim(),
      address: [
        form.querySelector('[name="address"]').value.trim(),
        form.querySelector('[name="locality"]').value.trim(),
        form.querySelector('[name="city"]').value.trim()
      ].filter(Boolean).join(', '),
      phone: form.querySelector('[name="contact_phone"]').value.trim()
    };
    var selected = timeField.options[timeField.selectedIndex];
    var parts = dateField.value.split('-').map(Number);
    var dateAtNoonUtc = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2], 12));
    var dateLabel = new Intl.DateTimeFormat('en', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC'}).format(dateAtNoonUtc);
    values.when = dateLabel + ' · ' + (selected ? selected.text : '') + ' (' + (form.dataset.timezone || 'local time') + ')';
    Object.keys(values).forEach(function (key) {
      var target = review.querySelector('[data-review="' + key + '"]');
      if (target) target.textContent = values[key];
    });
    entry.hidden = true;
    review.hidden = false;
    if (progressSteps.length) setProgress(3);
    reviewButton.hidden = true;
    if (confirmButton) {
      confirmButton.hidden = false;
      confirmButton.focus();
    }
  });

  if (editButton) editButton.addEventListener('click', function () {
    resetReview();
    if (progressSteps.length) setProgress(2);
    if (reviewButton) reviewButton.focus();
  });
});
