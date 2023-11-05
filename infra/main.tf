# Terraform variables

variable "project" {
  type = string
}

variable "region" {
  type = string
}

variable "location" {
  type = string
}

variable "sa_account_file" {
  type = string
}

variable "sa_name" {
  type = string
}

variable "maps_api_token" {}

variable "telegram_api_token" {}

provider "google" {
  credentials = file("../var/${var.sa_account_file}")
  project     = var.project
  region      = var.region
}


# Secrets

resource "google_secret_manager_secret" "maps_api_token" {
  secret_id = "maps-api-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "maps_api_token_secret_version_data" {
  secret      = google_secret_manager_secret.maps_api_token.name
  secret_data = var.maps_api_token
}

resource "google_secret_manager_secret_iam_member" "maps_api_token_secret_access" {
  secret_id  = google_secret_manager_secret.maps_api_token.id
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${var.sa_name}"
  depends_on = [google_secret_manager_secret.maps_api_token]
}

resource "google_secret_manager_secret" "telegram_api_token" {
  secret_id = "telegram-api-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "telegram_api_token_secret_version_data" {
  secret      = google_secret_manager_secret.telegram_api_token.name
  secret_data = var.telegram_api_token
}

resource "google_secret_manager_secret_iam_member" "telegram_api_token_secret_access" {
  secret_id  = google_secret_manager_secret.telegram_api_token.id
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${var.sa_name}"
  depends_on = [google_secret_manager_secret.telegram_api_token]
}


# IAM service accounts

resource "google_service_account" "service_account" {
  account_id = "iot-project-sa"
  project    = var.project
}

resource "google_project_iam_member" "pubsub_editor" {
  project = var.project
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}

resource "google_project_iam_member" "secretmanager_secret_accessor" {
  project = var.project
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.service_account.email}"
}


# Pub/Sub Avro schemas

resource "google_pubsub_schema" "iot_events_schema" {
  name       = "iot-events-schema"
  type       = "AVRO"
  definition = file("avro_schemas/iot_events_schema.avsc")
}

resource "google_pubsub_schema" "domain_logs_schema" {
  name       = "domain-logs-schema"
  type       = "AVRO"
  definition = file("avro_schemas/domain_logs_schema.avsc")
}

resource "google_pubsub_schema" "journeys_schema" {
  name       = "journeys-schema"
  type       = "AVRO"
  definition = file("avro_schemas/journeys_schema.avsc")
}


# Pub/Sub topics

resource "google_pubsub_topic" "iot_events_topic" {
  name = "iot-events"

  depends_on = [google_pubsub_schema.iot_events_schema]
  schema_settings {
    schema   = "projects/${var.project}/schemas/iot-events-schema"
    encoding = "JSON"
  }
}

resource "google_pubsub_topic" "domain_logs_topic" {
  name = "domain-logs"

  depends_on = [google_pubsub_schema.domain_logs_schema]
  schema_settings {
    schema   = "projects/${var.project}/schemas/domain-logs-schema"
    encoding = "JSON"
  }
}

resource "google_pubsub_topic" "journeys_topic" {
  name = "journeys"

  depends_on = [google_pubsub_schema.domain_logs_schema]
  schema_settings {
    schema   = "projects/${var.project}/schemas/${google_pubsub_schema.journeys_schema.name}"
    encoding = "JSON"
  }
}


# Pub/Sub subscriptions

resource "google_pubsub_subscription" "domain_logs_subscription" {
  name       = "domain-logs-big-query-sync"
  topic      = "projects/${var.project}/topics/domain-logs"
  depends_on = [google_pubsub_topic.domain_logs_topic, google_bigquery_table.domain_logs_table]

  bigquery_config {
    drop_unknown_fields = false
    table               = "${var.project}.iot_events_data.domain-logs"
    use_topic_schema    = true
    write_metadata      = false
  }

  timeouts {}
}

resource "google_pubsub_subscription" "iot_events_subscription" {
  name       = "iot-events-big-query-sync"
  topic      = "projects/${var.project}/topics/iot-events"
  depends_on = [google_pubsub_topic.iot_events_topic, google_bigquery_table.iot_events_table]

  bigquery_config {
    drop_unknown_fields = false
    table               = "${var.project}.iot_events_data.iot-events"
    use_topic_schema    = true
    write_metadata      = false
  }

  timeouts {}
}

resource "google_pubsub_subscription" "journeys_subscription" {
  name       = "journeys-big-query-sync"
  topic      = "projects/${var.project}/topics/${google_pubsub_topic.journeys_topic.name}"
  depends_on = [google_pubsub_topic.iot_events_topic, google_bigquery_table.journeys_table]

  bigquery_config {
    drop_unknown_fields = false
    table               = "${var.project}.iot_events_data.journeys"
    use_topic_schema    = true
    write_metadata      = false
  }

  timeouts {}
}

resource "google_pubsub_subscription" "domain_logs_notifications_subscription" {
  name       = "domain-logs-notifications"
  topic      = "projects/${var.project}/topics/domain-logs"
  depends_on = [google_pubsub_topic.domain_logs_topic, google_cloud_run_v2_service.notifications_server_cloud_run]

  ack_deadline_seconds = 10

  filter = "attributes.type = \"truck_not_found\""

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.notifications_server_cloud_run.uri}/notifications"

    attributes = {
      x-goog-version = "v1"
    }
  }

  timeouts {}
}


# Big Query resources

resource "google_bigquery_dataset" "iot_events_data_dataset" {
  dataset_id                  = "iot_events_data"
  default_table_expiration_ms = 2592000000
  delete_contents_on_destroy  = true
  is_case_insensitive         = false
  labels                      = {}
  location                    = "europe-central2"
  max_time_travel_hours       = "168"
  project                     = var.project

  access {
    role          = "OWNER"
    user_by_email = "rostix2000@gmail.com"
  }
  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
  access {
    role          = "READER"
    special_group = "projectReaders"
  }
  access {
    role          = "WRITER"
    special_group = "projectWriters"
  }

  timeouts {}
}

resource "google_bigquery_table" "domain_logs_table" {
  depends_on = [google_bigquery_dataset.iot_events_data_dataset]

  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  labels                   = {}
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "REQUIRED"
        name = "type"
        type = "STRING"
      },
      {
        mode = "REQUIRED"
        name = "data"
        type = "STRING"
      },
      {
        mode = "REQUIRED"
        name = "timestamp"
        type = "INTEGER"
      },
    ]
  )
  table_id = "domain-logs"
}

resource "google_bigquery_table" "journeys_table" {
  depends_on = [google_bigquery_dataset.iot_events_data_dataset]

  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  labels                   = {}
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "REQUIRED"
        name = "truck_id"
        type = "INTEGER"
      },
      {
        mode = "REQUIRED"
        name = "journey_id"
        type = "INTEGER"
      },
      {
        mode = "REQUIRED"
        name = "route_geography"
        type = "STRING"
      },
    ]
  )
  table_id = "journeys"
}

resource "google_bigquery_table" "iot_events_table" {
  depends_on               = [google_bigquery_dataset.iot_events_data_dataset]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  labels                   = {}
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "REQUIRED"
        name = "truck_id"
        type = "INTEGER"
      },
      {
        mode = "REQUIRED"
        name = "lat"
        type = "FLOAT"
      },
      {
        mode = "REQUIRED"
        name = "lon"
        type = "FLOAT"
      },
      {
        mode = "REQUIRED"
        name = "timestamp"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "color"
        type = "STRING"
      },
    ]
  )
  table_id = "iot-events"
}

resource "google_bigquery_table" "domain_logs_with_json_data_view" {
  depends_on               = [google_bigquery_table.domain_logs_table]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  labels                   = {}
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "type"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "data_json"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "timestamp_datetime"
        type = "DATETIME"
      },
    ]
  )
  table_id = "domain-logs-with-json-data"

  view {
    query          = "SELECT type, SAFE.PARSE_JSON(data) AS data_json, CAST(TIMESTAMP_MILLIS(timestamp) as DATETIME) as timestamp_datetime  FROM `${var.project}.iot_events_data.domain-logs` LIMIT 1000"
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "journey_dispatched_domain_logs_view" {
  depends_on               = [google_bigquery_table.domain_logs_with_json_data_view]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "type"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "truck_id"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "journey_id"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "origin_address"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "destination_address"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "expected_duration_in_seconds"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "timestamp_datetime"
        type = "DATETIME"
      },
    ]
  )
  table_id = "journey-dispatched-domain-logs"

  view {
    query          = <<-EOT
            SELECT
              type,
              data_json.truck_id,
              data_json.journey_id,
              data_json.origin_address,
              data_json.destination_address,
              data_json.expected_duration_in_seconds,
              timestamp_datetime
            FROM `${var.project}.iot_events_data.domain-logs-with-json-data`
            WHERE type = 'journey_dispatched'
            LIMIT 1000
        EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "journey_finished_domain_logs_view" {
  depends_on               = [google_bigquery_table.domain_logs_with_json_data_view]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "type"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "truck_id"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "journey_id"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "origin_address"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "destination_address"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "timestamp_datetime"
        type = "DATETIME"
      },
    ]
  )
  table_id = "journey-finished-domain-logs"

  view {
    query          = <<-EOT
            SELECT
              type,
              data_json.truck_id,
              data_json.journey_id,
              data_json.origin_address,
              data_json.destination_address,
              timestamp_datetime
            FROM `${var.project}.iot_events_data.domain-logs-with-json-data`
            WHERE type = 'journey_finished'
            LIMIT 1000
        EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "tts_state_domain_logs_view" {
  depends_on               = [google_bigquery_table.domain_logs_with_json_data_view]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "type"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "number_of_journeys"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "busy_trucks"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "free_trucks"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "trucks"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "timestamp_datetime"
        type = "DATETIME"
      },
    ]
  )
  table_id = "tts-state-domain-logs"

  view {
    query          = <<-EOT
            SELECT
              type,
              INT64(data_json.number_of_journeys) as number_of_journeys,
              INT64(data_json.fleet.busy_trucks) as busy_trucks,
              INT64(data_json.fleet.free_trucks) as free_trucks,
              data_json.fleet.trucks,
              timestamp_datetime
            FROM `${var.project}.iot_events_data.domain-logs-with-json-data`
            WHERE type = 'tts_state' AND timestamp_datetime > DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 60 MINUTE)
            LIMIT 1000
        EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "truck_not_found_domain_logs_view" {
  depends_on               = [google_bigquery_table.domain_logs_with_json_data_view]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "type"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "origin_address"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "destination_address"
        type = "JSON"
      },
      {
        mode = "NULLABLE"
        name = "load_weight"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "timestamp_datetime"
        type = "DATETIME"
      },
    ]
  )
  table_id = "truck-not-found-domain-logs"

  view {
    query          = <<-EOT
            SELECT
              type,
              data_json.origin_address,
              data_json.destination_address,
              INT64(data_json.load_weight) as load_weight,
              timestamp_datetime
            FROM `${var.project}.iot_events_data.domain-logs-with-json-data`
            WHERE type = 'truck_not_found'
            LIMIT 1000
        EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "latest_trucks_data_view" {
  depends_on               = [google_bigquery_table.tts_state_domain_logs_view]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "id"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "in_journey"
        type = "BOOLEAN"
      },
      {
        mode = "NULLABLE"
        name = "location"
        type = "GEOGRAPHY"
      },
    ]
  )
  table_id = "latest-trucks-data"

  view {
    query          = <<-EOT
            SELECT
             INT64(trucks_data.id) as id,
             BOOL(trucks_data.in_journey) as in_journey,
             ST_GEOGPOINT(FLOAT64(trucks_data.location.lon), FLOAT64(trucks_data.location.lat)) as location
             FROM
              (
                SELECT trucks
                FROM `${var.project}.iot_events_data.tts-state-domain-logs`
                ORDER BY timestamp_datetime desc
                LIMIT 1
                ) as domain_logs,
              UNNEST(JSON_EXTRACT_ARRAY(trucks, '$')) AS trucks_data
        EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "iot_events_with_geo_view" {
  depends_on               = [google_bigquery_table.iot_events_table]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "truck_id"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "lat"
        type = "FLOAT"
      },
      {
        mode = "NULLABLE"
        name = "lon"
        type = "FLOAT"
      },
      {
        mode = "NULLABLE"
        name = "timestamp"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "color"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "timestamp_datetime"
        type = "DATETIME"
      },
      {
        mode = "NULLABLE"
        name = "geopoint"
        type = "GEOGRAPHY"
      },
    ]
  )
  table_id = "iot-events-with-geo"

  view {
    query          = <<-EOT
            SELECT
              *,
              CAST(TIMESTAMP_MILLIS(timestamp) as DATETIME) as timestamp_datetime,
              ST_GEOGPOINT(lon, lat) AS geopoint,
            FROM
              `${var.project}.iot_events_data.iot-events`
        EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "journeys_with_geo_view" {
  depends_on               = [google_bigquery_table.journeys_table]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "truck_id"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "journey_id"
        type = "INTEGER"
      },
      {
        mode = "NULLABLE"
        name = "route_geography"
        type = "GEOGRAPHY"
      },
    ]
  )
  table_id = "journeys-with-geo"

  view {
    query          = <<-EOT
        SELECT
          truck_id,
          journey_id,
          ST_GEOGFROMTEXT(route_geography) as route_geography
        FROM `${var.project}.iot_events_data.journeys`
        LIMIT 1000
      EOT
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "business_value_domain_logs_view" {
  depends_on               = [google_bigquery_table.domain_logs_table]
  dataset_id               = google_bigquery_dataset.iot_events_data_dataset.dataset_id
  deletion_protection      = false
  project                  = var.project
  require_partition_filter = false
  schema = jsonencode(
    [
      {
        mode = "NULLABLE"
        name = "type"
        type = "STRING"
      },
      {
        mode = "NULLABLE"
        name = "time"
        type = "DATETIME"
      },
    ]
  )
  table_id = "business-value-domain-logs"

  view {
    query          = <<-EOT
        SELECT
          type,
          CAST(TIMESTAMP_MILLIS(timestamp) as DATETIME) as time
        FROM `cloud-computing-project-403820.iot_events_data.domain-logs`
        WHERE type != 'tts_state'
        LIMIT 1000
      EOT
    use_legacy_sql = false
  }
}


# Cloud Run resources

data "google_iam_policy" "no_auth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_v2_service" "tts_server_cloud_run" {
  name     = "tts-server"
  location = var.location
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.service_account.email

    scaling {
      max_instance_count = 1
      min_instance_count = 1
    }

    containers {
      image = "rostmoguchiy/tts-server"
      ports {
        container_port = 80
      }
      env {
        name = "MAPS_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.maps_api_token.secret_id
            version = "1"
          }
        }
      }
      env {
        name = "TELEGRAM_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_api_token.secret_id
            version = "1"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  depends_on = [
    google_secret_manager_secret_version.maps_api_token_secret_version_data,
    google_secret_manager_secret_version.telegram_api_token_secret_version_data,
  ]
}

resource "google_cloud_run_service_iam_policy" "tts_server_noauth" {
  location = google_cloud_run_v2_service.tts_server_cloud_run.location
  project  = google_cloud_run_v2_service.tts_server_cloud_run.project
  service  = google_cloud_run_v2_service.tts_server_cloud_run.name

  policy_data = data.google_iam_policy.no_auth.policy_data
}

resource "google_cloud_run_v2_service" "notifications_server_cloud_run" {
  name     = "notifications-server"
  location = var.location
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.service_account.email
    scaling {
      max_instance_count = 1
      min_instance_count = 1
    }

    containers {
      image = "rostmoguchiy/notifications-server"
      ports {
        container_port = 80
      }
      env {
        name = "MAPS_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.maps_api_token.secret_id
            version = "1"
          }
        }
      }
      env {
        name = "TELEGRAM_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_api_token.secret_id
            version = "1"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  depends_on = [
    google_secret_manager_secret_version.maps_api_token_secret_version_data,
    google_secret_manager_secret_version.telegram_api_token_secret_version_data,
  ]
}

resource "google_cloud_run_service_iam_policy" "notifications_server_noauth" {
  location = google_cloud_run_v2_service.notifications_server_cloud_run.location
  project  = google_cloud_run_v2_service.notifications_server_cloud_run.project
  service  = google_cloud_run_v2_service.notifications_server_cloud_run.name

  policy_data = data.google_iam_policy.no_auth.policy_data
}
