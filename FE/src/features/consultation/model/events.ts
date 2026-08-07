export const CONSULTATIONS_CHANGED_EVENT = "m2m:consultations-changed";

export function notifyConsultationsChanged() {
  window.dispatchEvent(new Event(CONSULTATIONS_CHANGED_EVENT));
}

