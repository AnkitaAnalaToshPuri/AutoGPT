"use client";

import { usePushNotifications } from "./usePushNotifications";

export function PushNotificationProvider() {
  usePushNotifications();
  return null;
}
