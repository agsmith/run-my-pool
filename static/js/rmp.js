async function addEntry(count, user) {
    try {
        const entry = {
            entry_name: user.toString() + " #" +count.toString(),
            active_status: 'active',
            user_id: 10
        }
        const response = await fetch('/add-entry', {
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
        const response = await fetch('/add-pick/' + pick_id, {
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
        url = '/delete-entry/' + entry_id;
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
                const errorData = await resp.json();
                alert(errorData.error || 'Error submitting pick. Please try again.');
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
        try {
            const resp = await fetch(`/schedule/${weekNum}?pick_id=${pickId}`);
            
            if (!resp.ok) {
                const errorData = await resp.json();
                if (errorData.currentGameStarted) {
                    alert(errorData.error || 'Cannot change this pick - the current game has already started');
                    return; // Don't show the overlay
                } else if (errorData.deadlinePassed) {
                    alert(errorData.error || 'Cannot change this pick - the weekly deadline has passed');
                    return; // Don't show the overlay
                } else {
                    alert('Error loading schedule. Please try again.');
                    return;
                }
            }
            
            const games = await resp.json();

            let gamesHtml = games.games.map(function(game, id) {
                let homeDisabled = game.homeDisabled ? 'disabled' : '';
                let awayDisabled = game.awayDisabled ? 'disabled' : ''; 
                let homeSelectable = game.homeSelectable ? 'selectable-logo' : '';
                let awaySelectable = game.awaySelectable ? 'selectable-logo' : '';
                
                // Determine the reason for disabling
                let homeTitle = '';
                let awayTitle = '';
                
                if (game.gameStarted) {
                    homeTitle = 'Game has already started';
                    awayTitle = 'Game has already started';
                } else if (game.homeDisabled) {
                    homeTitle = 'This team has already been selected for this entry';
                }
                
                if (game.gameStarted) {
                    awayTitle = 'Game has already started';
                } else if (game.awayDisabled && !game.gameStarted) {
                    awayTitle = 'This team has already been selected for this entry';
                }
                
                return `<div class='overlay-game ${game.gameStarted ? 'game-started' : ''}' data-game-id='${game.game_id}'>
                    <img src='${game.home_team.logo}' class='overlay-game-logo ${homeSelectable} ${homeDisabled}' data-team='${game.home_team.abbrv}' data-game-id='${game.game_id}' tabindex='0' title='${homeTitle}'>
                    <div class='overlay-game-team'>${game.home_team.abbrv}</div>
                    <div class='overlay-game-vs'>vs</div>
                    <img src='${game.away_team.logo}' class='overlay-game-logo ${awaySelectable} ${awayDisabled}' data-team='${game.away_team.abbrv}' data-game-id='${game.game_id}' tabindex='0' title='${awayTitle}'>
                    <div class='overlay-game-team'>${game.away_team.abbrv}</div>
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
                    // Don't allow selection of disabled teams
                    if (logo.classList.contains('disabled')) {
                        return;
                    }
                    
                    if (selectedLogo === logo) {
                        // Unselect if already selected
                        logo.classList.remove('selected-logo');
                        selectedLogo = null;
                        document.getElementById('submit-pick-form').team.value = '';
                        document.getElementById('submit-pick-form').game_id.value = '';
                        submitBtn.disabled = true;
                    } else {
                        // Unselect previous
                        if (selectedLogo) selectedLogo.classList.remove('selected-logo');
                        // Select new
                        logo.classList.add('selected-logo');
                        selectedLogo = logo;
                        document.getElementById('submit-pick-form').team.value = logo.dataset.team;
                        document.getElementById('submit-pick-form').game_id.value = logo.dataset.gameId;
                        submitBtn.disabled = false;
                    }
                });
            });
            
            // Reset selection on overlay open
            if (document.getElementById('submit-pick-form').team) {
                document.getElementById('submit-pick-form').team.value = '';
                submitBtn.disabled = true;
            }
            
        } catch (error) {
            console.error('Error loading schedule:', error);
            alert('Network error. Please try again.');
        }
    });
});

