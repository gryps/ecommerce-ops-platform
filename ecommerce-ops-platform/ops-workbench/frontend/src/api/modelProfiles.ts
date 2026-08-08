import type { ModelProfile, ModelProfilesResponse } from "../types";
import { api } from "./client";

export function fetchModelProfiles() {
  return api<ModelProfilesResponse>("/model-profiles");
}

export function fetchModelList(profile: ModelProfile) {
  return api<{ models: string[] }>("/model-profiles/models", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

export function saveModelProfile(profile: ModelProfile) {
  return api<ModelProfile>(`/model-profiles/${profile.stage}`, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}
