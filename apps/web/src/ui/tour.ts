/** Tour onboarding — stub cho build; mở rộng sau khi có driver.js. */
const KEY = "nq_tour_done";

export function datCoTourSauDangKy(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(KEY);
}

export function chayLaiTour(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(KEY);
}

export function daBoTour(): boolean {
  if (typeof localStorage === "undefined") return true;
  return localStorage.getItem(KEY) === "1";
}

export function danhDauDaBoTour(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(KEY, "1");
}
