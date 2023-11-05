output "tts_server_service_uri" {
  value = "${google_cloud_run_v2_service.tts_server_cloud_run.uri}/docs"
}

output "notification_server_service_uri" {
  value = "${google_cloud_run_v2_service.notifications_server_cloud_run.uri}/docs"
}
