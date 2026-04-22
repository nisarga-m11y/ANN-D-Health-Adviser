import { apiClient } from "./client";

export async function sendEmailOtp(email) {
  const { data } = await apiClient.post("/auth/otp/email/send/", { email });
  return data;
}

export async function verifyEmailOtp(email, otp) {
  const { data } = await apiClient.post("/auth/otp/email/verify/", { email, otp });
  return data;
}
