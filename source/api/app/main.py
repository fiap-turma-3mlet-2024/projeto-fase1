from os import getenv
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, validator, Field, field_validator
import requests
import string
import secrets
from datetime import datetime, timedelta

from pydantic_core.core_schema import ValidationInfo

# Environment variables
dag_id = getenv("AIRFLOW_DAG_ID")
airflow_url = getenv("AIRFLOW_URL")
username = getenv("AIRFLOW_USERNAME")
password = getenv("AIRFLOW_PASSWORD")

# Constants for date format
date_format = "%Y-%m-%dT%H:%M:%SZ"
date_format_dag_id = "%Y%m%d%H%M%S"

TABS = {
    "produção": "opt_02",
    "processamento": "opt_03",
    "comercialização": "opt_04",
    "importação": "opt_05",
    "exportação": "opt_06",
    "publicação": "opt_07",
}


# Request body for job start
class StartJobRequest(BaseModel):
    year_start: int = Field(..., ge=1990, description="The start year", alias="yearStart")
    year_end: int = Field(..., ge=1990, description="The end year", alias="yearEnd")

    @field_validator('year_end')
    @classmethod
    def check_years(cls, year_end, info: ValidationInfo) -> int:
        year_start = info.data.get('year_start')
        if year_start is not None and year_end < year_start:
            raise ValueError('yearEnd must be greater than or equal to yearStart')
        return year_end


def generate_secure_random_string(length):
    characters = string.ascii_letters + string.digits  # Use letters and digits
    secure_random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return secure_random_string


app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "OK"}


@app.post("/jobs")
def start_job(request: StartJobRequest):
    date_start = datetime.now()

    results = []

    for year in range(request.year_start, request.year_end + 1):
        for tab in TABS.keys():
            request_body = {
                "dag_run_id": f"extract_run_{date_start.strftime(date_format_dag_id)}_{generate_secure_random_string(10)}",
                "conf": {
                    "year": year,
                    "tab": tab
                },
                "note": f"Extraction started through api, year {year}, option {tab}"
            }

            response = requests.post(f'{airflow_url}/api/v1/dags/{dag_id}/dagRuns', json=request_body,
                                     auth=(username, password))

            json_response = response.json()

            if response.status_code == 200:
                results += [{
                    "dag_run_id": json_response['dag_run_id'],
                    "status": json_response['state'],
                    "params": {
                        "year": year,
                        "tab": tab
                    }
                }]

    return {
        "status": "success",
        "results": results
    }


@app.get("/jobs/{dag_run_id}")
def get_job_status(dag_run_id: str):
    response = requests.get(f'{airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}', auth=(username, password))

    if response.status_code == 200:
        json_response = response.json()
        print(json_response)
        return {
            "status": "success",
            "result": {
                "dag_run_id": json_response['dag_run_id'],
                "status": json_response['state'],
                "execution_date": json_response['execution_date'],
                "start_date": json_response['start_date'],
                "end_date": json_response['end_date'],
                "note": json_response['note']
            }
        }
    elif response.status_code == 404:
        return {
            "status": "error",
            "message": "Dag run not found"
        }
    else:
        return {
            "status": "error",
            "message": "Error while fetching dag run",
            "result": {
                "response": response.text,
                "status_code": response.status_code
            }
        }
