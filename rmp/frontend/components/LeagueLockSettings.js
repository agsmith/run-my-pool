import { useEffect, useMemo, useState } from 'react';

export const TIMEZONES = [
  { label: 'Eastern Time (ET)', iana: 'America/New_York' },
  { label: 'Central Time (CT)', iana: 'America/Chicago' },
  { label: 'Mountain Time (MT)', iana: 'America/Denver' },
  { label: 'Pacific Time (PT)', iana: 'America/Los_Angeles' },
  { label: 'UTC', iana: 'UTC' },
];

export const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const pad = (value) => String(value).padStart(2, '0');

const openNativePicker = (event) => {
  try {
    event.currentTarget.showPicker?.();
  } catch {
    // Browsers without programmatic picker support still use the native control.
  }
};

const asUtcDate = (value) => {
  if (!value) return null;
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value.replace(' ', 'T')}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
};

export function toUtcIso(dateStr, timeStr, timeZone) {
  if (!dateStr || !timeStr) return null;
  const [year, month, day] = dateStr.split('-').map(Number);
  const [hour, minute] = timeStr.split(':').map(Number);
  if (![year, month, day, hour, minute].every(Number.isFinite)) return null;

  let guess = Date.UTC(year, month - 1, day, hour, minute);
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = Object.fromEntries(formatter.formatToParts(new Date(guess)).map(({ type, value }) => [type, value]));
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute));
    guess += Date.UTC(year, month - 1, day, hour, minute) - represented;
  }
  return new Date(guess).toISOString().replace('T', ' ').replace('.000Z', '');
}

function localDateTimeFields(value, timeZone) {
  const date = asUtcDate(value);
  if (!date) return { date: '', time: '13:00' };
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date).map(({ type, value: part }) => [type, part]));
  return { date: `${parts.year}-${parts.month}-${parts.day}`, time: `${parts.hour}:${parts.minute}` };
}

function formatClockTime(value) {
  const [hour = 0, minute = '00'] = String(value || '13:00').split(':');
  const numericHour = Number(hour);
  return `${numericHour % 12 || 12}:${minute} ${numericHour < 12 ? 'AM' : 'PM'}`;
}

function formatRegistrationLock(value, timeZone) {
  const date = asUtcDate(value);
  if (!date) return null;
  return new Intl.DateTimeFormat('en-US', {
    timeZone,
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  }).format(date);
}

function Modal({ title, description, onClose, children, onSave, saving }) {
  useEffect(() => {
    const closeOnEscape = (event) => event.key === 'Escape' && onClose();
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  return (
    <div className="lock-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="lock-modal" role="dialog" aria-modal="true" aria-labelledby="lock-modal-title">
        <header className="lock-modal__header">
          <div>
            <span>Pool settings</span>
            <h3 id="lock-modal-title">{title}</h3>
            <p>{description}</p>
          </div>
          <button type="button" className="lock-modal__close" aria-label="Close dialog" onClick={onClose}>×</button>
        </header>
        <div className="lock-modal__fields">{children}</div>
        <footer className="lock-modal__footer">
          <button type="button" className="lock-modal__cancel" onClick={onClose}>Cancel</button>
          <button type="button" onClick={onSave} disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
        </footer>
      </section>
    </div>
  );
}

export default function LeagueLockSettings({ league, onSave }) {
  const leagueTimezone = league?.lock_timezone || 'America/New_York';
  const [activeModal, setActiveModal] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [weekly, setWeekly] = useState({ day: 6, time: '13:00', timezone: leagueTimezone });
  const [registration, setRegistration] = useState({ date: '', time: '13:00', timezone: leagueTimezone });

  useEffect(() => {
    if (!league) return;
    const timezone = league.lock_timezone || 'America/New_York';
    setWeekly({
      day: league.lock_day_of_week ?? 6,
      time: (league.lock_time_of_day || '13:00').slice(0, 5),
      timezone,
    });
    setRegistration({ ...localDateTimeFields(league.join_lock_time, timezone), timezone });
  }, [league]);

  const registrationLabel = useMemo(
    () => formatRegistrationLock(league?.join_lock_time, leagueTimezone),
    [league?.join_lock_time, leagueTimezone],
  );

  const saveWeekly = async () => {
    setSaving(true);
    setMessage('');
    try {
      await onSave({
        lock_day_of_week: Number(weekly.day),
        lock_time_of_day: weekly.time,
        lock_timezone: weekly.timezone,
      });
      setMessage('Weekly pick lock updated.');
      setActiveModal(null);
    } catch (error) {
      setMessage(error.message || 'Unable to update the weekly pick lock.');
    } finally {
      setSaving(false);
    }
  };

  const saveRegistration = async () => {
    const joinLock = toUtcIso(registration.date, registration.time, registration.timezone);
    if (!joinLock) {
      setMessage('Enter a valid registration deadline.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      await onSave({ join_lock_time: joinLock });
      setMessage('Pool registration lock updated.');
      setActiveModal(null);
    } catch (error) {
      setMessage(error.message || 'Unable to update the registration lock.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="admin-lock-settings" aria-labelledby="lock-settings-title">
      <div className="admin-lock-settings__heading">
        <div>
          <span>Pool deadlines</span>
          <h4 id="lock-settings-title">Lock Times</h4>
          <p>Review the active deadlines before making a change.</p>
        </div>
      </div>
      <div className="admin-lock-settings__grid">
        <article className="lock-setting-card">
          <span className="lock-setting-card__eyebrow">Weekly pick lock</span>
          <strong>{DAYS_OF_WEEK[league?.lock_day_of_week ?? 6]} at {formatClockTime(league?.lock_time_of_day)}</strong>
          <small>{TIMEZONES.find(({ iana }) => iana === leagueTimezone)?.label || leagueTimezone}</small>
          <p>Picks and the line used for defaults lock at this time each week.</p>
          <button type="button" onClick={() => setActiveModal('weekly')}>Change weekly lock</button>
        </article>
        <article className="lock-setting-card">
          <span className="lock-setting-card__eyebrow">Pool registration lock</span>
          <strong>{registrationLabel || 'Not set'}</strong>
          <small>{registrationLabel ? 'New members and entries close at this deadline.' : 'Registration is currently open.'}</small>
          <p>After this deadline, users cannot join the pool or add or delete entries.</p>
          <button type="button" onClick={() => setActiveModal('registration')}>Change registration lock</button>
        </article>
      </div>
      {message && <p className="admin-lock-settings__message" role="status">{message}</p>}

      {activeModal === 'weekly' && (
        <Modal title="Change weekly pick lock" description="Choose the recurring day and time when picks lock each week." onClose={() => setActiveModal(null)} onSave={saveWeekly} saving={saving}>
          <label>Day of week<select value={weekly.day} onChange={(event) => setWeekly({ ...weekly, day: Number(event.target.value) })}>{DAYS_OF_WEEK.map((day, index) => <option key={day} value={index}>{day}</option>)}</select></label>
          <label>Time<select value={weekly.time} onChange={(event) => setWeekly({ ...weekly, time: event.target.value })}>{Array.from({ length: 48 }, (_, index) => { const hour = Math.floor(index / 2); const minute = index % 2 ? '30' : '00'; const value = `${pad(hour)}:${minute}`; return <option key={value} value={value}>{formatClockTime(value)}</option>; })}</select></label>
          <label>Timezone<select value={weekly.timezone} onChange={(event) => setWeekly({ ...weekly, timezone: event.target.value })}>{TIMEZONES.map((timezone) => <option key={timezone.iana} value={timezone.iana}>{timezone.label}</option>)}</select></label>
        </Modal>
      )}
      {activeModal === 'registration' && (
        <Modal title="Change registration lock" description="Set the final date and time when members can join or manage entries." onClose={() => setActiveModal(null)} onSave={saveRegistration} saving={saving}>
          <label>Date<input aria-label="Registration lock date" type="date" value={registration.date} onClick={openNativePicker} onChange={(event) => setRegistration({ ...registration, date: event.target.value })} /></label>
          <label>Time<input aria-label="Registration lock time" type="time" value={registration.time} onClick={openNativePicker} onChange={(event) => setRegistration({ ...registration, time: event.target.value })} /></label>
          <label>Timezone<select value={registration.timezone} onChange={(event) => setRegistration({ ...registration, timezone: event.target.value })}>{TIMEZONES.map((timezone) => <option key={timezone.iana} value={timezone.iana}>{timezone.label}</option>)}</select></label>
        </Modal>
      )}
    </section>
  );
}
