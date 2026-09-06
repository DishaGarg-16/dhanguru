/**
 * Returns a persistent anonymous guest ID stored in localStorage.
 * Ensures each reviewer/visitor has their own isolated session checkpoint
 * and watchlist without overwriting other reviewers' timers.
 */
export function getGuestUserId() {
  try {
    let uid = localStorage.getItem('dhanguru_guest_uid');
    if (!uid || !uid.startsWith('guest_')) {
      uid = 'guest_' + Math.random().toString(36).substring(2, 8);
      localStorage.setItem('dhanguru_guest_uid', uid);
    }
    return uid;
  } catch {
    return 'default_user';
  }
}
