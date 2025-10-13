// Utility to manage session storage consistently across the app

export const setSessionData = (key, value) => {
  sessionStorage.setItem(key, JSON.stringify(value));
};

export const getSessionData = (key) => {
  const data = sessionStorage.getItem(key);
  return data ? JSON.parse(data) : null;
};

export const clearSessionData = (key) => {
  sessionStorage.removeItem(key);
};

export const clearAllSessionData = () => {
  sessionStorage.clear();
};

