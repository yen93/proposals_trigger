/**
 * Bound to the "Proposal Automation Trigger Form". Fires the
 * proposal-router-hourly routine (trig_01VUXJpHGMMEAABsEAVdWjJG) immediately
 * on every new response, instead of waiting for its hourly cron.
 *
 * SETUP (see apps_script/README.md for the full walkthrough):
 *   1. Paste this file into the Form's Apps Script project.
 *   2. Project Settings -> Script Properties -> add a property named
 *      ROUTINE_FIRE_TOKEN with the bearer token value. Paste it directly
 *      into that UI field -- NEVER into this script's source, and never
 *      commit the real token to git.
 *   3. Triggers -> Add Trigger -> function "onFormSubmit", event source
 *      "From form", event type "On form submit" -> Save.
 */

const ROUTINE_FIRE_URL =
  "https://api.anthropic.com/v1/claude_code/routines/trig_01VUXJpHGMMEAABsEAVdWjJG/fire";

function onFormSubmit(e) {
  const token = PropertiesService.getScriptProperties().getProperty("ROUTINE_FIRE_TOKEN");
  if (!token) {
    console.error("ROUTINE_FIRE_TOKEN script property is not set -- see apps_script/README.md.");
    return;
  }

  const response = UrlFetchApp.fetch(ROUTINE_FIRE_URL, {
    method: "post",
    headers: {
      "Authorization": "Bearer " + token,
      "anthropic-version": "2023-06-01",
      "anthropic-beta": "experimental-cc-routine-2026-04-01",
    },
    contentType: "application/json",
    payload: JSON.stringify({ text: "Fired by Apps Script on new Form response." }),
    muteHttpExceptions: true,
  });

  const code = response.getResponseCode();
  if (code >= 200 && code < 300) {
    console.log("proposal-router-hourly fired successfully (HTTP " + code + ")");
  } else {
    console.error("Failed to fire proposal-router-hourly: HTTP " + code + " - " + response.getContentText());
  }
}
