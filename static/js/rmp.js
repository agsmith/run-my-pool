async function addEntry(count, user) {
    try {
        const entry = {
            entry_name: user.toString() + " #" +count.toString(),
            active_status: 'active',
            user_id: 10
        }
        const response = await fetch('/addEntry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(entry)
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('API Response:', data);
        console.log('count:', count);
        // Handle the API response data here
      } catch (error) {
        console.error('Error calling API:', error);
        // Handle errors during the API call
    }
}

async function addPick(pick_id) {
    try {
        const entry = {
            pick_id: pick_id
        }
        const response = await fetch('/addPick/' + pick_id, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('API Response:', data);
        console.log('count:', count);
        // Handle the API response data here
      } catch (error) {
        console.error('Error calling API:', error);
        // Handle errors during the API call
    }
}


async function delEntry(entry_id) {
    try {
        url = '/delEntry/' + entry_id;
        const response = await fetch(url, { method: 'DELETE' });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('API Response:', data);
        console.log('entry_id:', entry_id);
        // Handle the API response data here
      } catch (error) {
        console.error('Error calling API:', error);
        // Handle errors during the API call
    }
}
document.addEventListener('DOMContentLoaded', function () {
  console.log('rmp.js loaded');
  var modal = document.getElementById('delete-modal');
  var addEntryBtn = document.getElementById('add-entry-btn')
  var delEntryBtns = document.getElementsByClassName('delete-entry-btn')
  var addPickBtns = document.getElementsByClassName('add-pick')
  var cancelBtn = document.getElementById('delete-cancel-btn');
  var confirmBtn = document.getElementById('delete-confirm-btn');
  var currentRuleId = null;

  if(addEntryBtn) {
    addEntryBtn.addEventListener('click', function (e) {
      e.preventDefault();
      count = addEntryBtn.getAttribute('count') || 1;
      user = addEntryBtn.getAttribute('user') || 'Adam Smith';
      addEntry(count, user);
      location.reload();


   });
  }

  // Attach click listeners to all delete buttons with data-rule-id
  for (const btn of delEntryBtns) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      entry_id = btn.getAttribute('data-entry-id');
      delEntry(entry_id);
      location.reload();
    });
  }

  for (const btn of addPickBtns) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      pick_id = btn.getAttribute('pic-id');
      addPick(pick_id);
      // location.reload();
    });
  }
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
//  modal.addEventListener('click', function (e) {
//    if (e.target === modal) {
//      modal.style.display = 'none';
//      currentRuleId = null;
//    }
//  });
    document.getElementById('cancel-overlay-btn').addEventListener('click', function() {
        document.getElementById('pick-overlay').style.display = 'none';
    });
    document.getElementById('submit-pick-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        // Gather form data
        const form = e.target;
        const formData = new FormData(form);
        // Submit pick via AJAX
        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: formData
            });
            if (resp.ok) {
                document.getElementById('pick-overlay').style.display = 'none';
                window.location.reload(); // Refresh the page after successful pick submission
            } else {
                alert('Error submitting pick. Please try again.');
            }
        } catch (err) {
            alert('Network error. Please try again.');
        }
    });

    // Listen for custom event to show overlay and load schedule
    window.addEventListener('showPickOverlay', async function(e) {
        const weekNum = e.detail.weekNum;
        const pickId = e.detail.pickId;
        document.getElementById('overlay-week').textContent = weekNum;
        document.getElementById('submit-pick-form').pick_id.value = pickId;
        document.getElementById('submit-pick-form').week_num.value = weekNum;
        // Fetch schedule from API, passing pickId for context
        const resp = await fetch(`/api/schedule/${weekNum}?pick_id=${pickId}`);
        const games = await resp.json();

        // Fetch already picked teams for this entry
        // let pickedTeams = [];
        // if (window.entriesPicks && window.entriesPicks[pickId]) {
        //     pickedTeams = window.entriesPicks[pickId];
        // }

        let gamesHtml = games.games.map(function(game, id) {
            let homeDisabled = game.homeDisabled ? 'style="opacity:0.4;pointer-events:none;"' : '';
            let awayDisabled = game.awayDisabled ? 'style="opacity:0.4;pointer-events:none;"' : ''; 
            let homeSelectable = game.homeSelectable ? 'selectable-logo' : '';
            let awaySelectable = game.awaySelectable ? 'selectable-logo' : '';
            return `<div class='overlay-game'>
                <img src='${game.homeLogo}' class='overlay-game-logo ${homeSelectable}' data-team='${game.homeAbbrv}' tabindex='0' ${homeDisabled}>
                <div class='overlay-game-team'>${game.homeAbbrv}</div>
                <div class='overlay-game-vs'>vs</div>
                <img src='${game.awayLogo}' class='overlay-game-logo ${awaySelectable}' data-team='${game.awayAbbrv}' tabindex='0' ${awayDisabled}>
                <div class='overlay-game-team'>${game.awayAbbrv}</div>
                <div class='overlay-game-time'>${game.game_time}</div>
            </div>`;
        }).join('');
        document.getElementById('overlay-games').innerHTML = gamesHtml;
        document.getElementById('pick-overlay').style.display = 'flex';

        // Selection logic
        let selectedLogo = null;
        const submitBtn = document.getElementById('submit-pick-btn');
        submitBtn.disabled = true;
        document.querySelectorAll('.selectable-logo').forEach(function(logo) {
            logo.addEventListener('click', function() {
                if (selectedLogo === logo) {
                    // Unselect if already selected
                    logo.classList.remove('selected-logo');
                    selectedLogo = null;
                    document.getElementById('submit-pick-form').team.value = '';
                    submitBtn.disabled = true;
                } else {
                    // Unselect previous
                    if (selectedLogo) selectedLogo.classList.remove('selected-logo');
                    // Select new
                    logo.classList.add('selected-logo');
                    selectedLogo = logo;
                    document.getElementById('submit-pick-form').team.value = logo.dataset.team;
                    submitBtn.disabled = false;
                }
            });
        });
        // Reset selection on overlay open
        if (document.getElementById('submit-pick-form').team) {
            document.getElementById('submit-pick-form').team.value = '';
            submitBtn.disabled = true;
        }
    });
});

