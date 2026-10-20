#pragma once

#include "esp_err.h"
#include <stdbool.h>

esp_err_t health_check_run_self_test(void);
esp_err_t health_check_confirm_ota_success(void);
void health_check_trigger_rollback(void);
