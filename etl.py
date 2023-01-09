#!/usr/bin/env python
import os
import json
import urllib.parse
import csv
# import sqlite3
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv


def sf_api_create_token():
    params = {
        "grant_type": "password",
        "client_id": os.environ["SALESFORCE_CLIENT_ID"],
        "client_secret": os.environ["SALESFORCE_CLIENT_SECRET"],
        "username": os.environ["SALESFORCE_USERNAME"],
        "password": os.environ["SALESFORCE_PASSWORD"]
    }

    print("Requesting Authentication Token")
    r = requests.post(
        "https://login.salesforce.com/services/oauth2/token",
        params=params)
    with open("token.json", "w") as fh:
        json.dump(r.json(), fh)


def get_auth():
    # checks if we already have token.json file and uses that
    # API token remains valid for a while, not sure how long
    try:
        with open("token.json", "r") as fh:
            auth = json.load(fh)
    except FileNotFoundError:
        sf_api_create_token()
        with open("token.json", "r") as fh:
            auth = json.load(fh)
    return auth.get("access_token"), auth.get("instance_url")


def get_more_records(instance_url, headers, nextRecordsUrl, frames):
    # if more than 2,000 rows then it is more efficient to retrieve
    # data using composite request API
    print("Retrieving next page of records (10,000 per page)")
    composite_body = {
        "compositeRequest": [
            {
                "method": "GET",
                "referenceId": "req1",
                "url": nextRecordsUrl
            },
            {
                "method": "GET",
                "referenceId": "req2",
                "url": "@{req1.nextRecordsUrl}"
            },
            {
                "method": "GET",
                "referenceId": "req3",
                "url": "@{req2.nextRecordsUrl}"
            },
            {
                "method": "GET",
                "referenceId": "req4",
                "url": "@{req3.nextRecordsUrl}"
            },
            {
                "method": "GET",
                "referenceId": "req5",
                "url": "@{req4.nextRecordsUrl}"
            }
        ]
    }

    r = requests.post(f"{instance_url}/services/data/v52.0/composite",
                      headers=headers,
                      json=composite_body)
    r.raise_for_status()
    for response in r.json()["compositeResponse"]:
        # flatten json
        ndf = pd.json_normalize(response["body"]["records"])
        # remove attributes fields resulting from Account and Contact ID
        next_frame = ndf.loc[:, ~ndf.columns.str.contains("attributes.")]
        frames.append(next_frame)
        if response["body"]["done"]:
            return

    # if we're still here then there must be even more, do it again!
    get_more_records(
        instance_url,
        headers,
        r.json()["compositeResponse"][-1]["body"]["nextRecordsUrl"],
        frames
        )


def get_first_records(instance_url, headers, soql):
    # retrieves first 2,000 rows of query
    r = requests.get(
            f"{instance_url}/services/data/v52.0/query?q={soql}",
            headers=headers)
    r.raise_for_status()
    return r.json()


def replace_ids_with_names(instance_url, headers, df, fields_to_replace):
    # used for t1 and t2 diagnosis fields until a SOQL solution was found
    for field in fields_to_replace:
        print(f"Retrieving user data to replace IDs with names in {field}")
        user_ids = df[field].dropna().unique().tolist()
        id_string = "', '".join([str(id) for id in user_ids])
        soql = urllib.parse.quote(
            f"SELECT Id,Name FROM User WHERE Id IN ('{id_string}')")

        frames = []
        print("Retrieving first page of data (up to 2,000)")
        first_records = get_first_records(instance_url, headers, soql)

        # flatten json
        ndf = pd.json_normalize(first_records["records"])
        # remove attributes fields from nested objects like Account
        first_frame = ndf.loc[:, ~ndf.columns.str.contains("attributes.")]
        frames.append(first_frame)

        # if there are more than 2000 rows get the rest
        if first_records["done"] is False:
            nextRecordsUrl = first_records["nextRecordsUrl"]
            print("Retrieving next page of data (up to 10,000)")
            get_more_records(instance_url, headers, nextRecordsUrl, frames)

        users_df = pd.concat(frames)
        # drop empty columns
        users_df = users_df.dropna(axis=1, how='all')

        print(f"All user data retrieved, replacing IDs with names in {field}")
        df[field] = df[field].map(users_df.set_index("Id")["Name"])


def save_data(query_name, df):
    date_stamp = datetime.now().strftime("%Y%m%d")
    os.makedirs(os.path.join("archive", date_stamp), exist_ok=True)
    print(f"Saving as {query_name}.csv")
    df.to_csv(f"{query_name}.csv",
              encoding="utf-8",
              sep=",",
              quoting=csv.QUOTE_MINIMAL,
              index=False)
    print("Saving snapshot to archive")
    df.to_csv(os.path.join("archive",
                           date_stamp,
                           f"{query_name}_{date_stamp}.csv"),
              encoding="utf-8",
              sep=",",
              quoting=csv.QUOTE_MINIMAL,
              index=False)
    # during the early stages of this project it was useful to copy
    # the Salesforce data into a sqlite database, this is no longer needed
    # print("Writing data to kpi_data.db")
    # with sqlite3.connect("kpi_data.db") as conn:
    #     df.to_sql(f"{query_name}",
    #               conn,
    #               if_exists="replace",
    #               index=False)


def main():
    load_dotenv(".env")

    access_token, instance_url = get_auth()

    # create auth header for queries
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    # get SOQL queries and column mapping from queries.json
    with open("queries.json", "r") as fh:
        query_settings = json.load(fh)

    # for each query get data, combine and write to CSV
    for query in query_settings["queries"]:
        frames = []
        query_name = query["name"]
        soql = urllib.parse.quote(query["soql"])

        print(f"Retrieving first 2,000 records of {query_name}")
        first_records = get_first_records(instance_url, headers, soql)

        # flatten json
        ndf = pd.json_normalize(first_records["records"])
        # remove attributes fields from nested objects like Account
        first_frame = ndf.loc[:, ~ndf.columns.str.contains("attributes.")]
        frames.append(first_frame)

        # if there are more than 2000 rows get the rest
        if first_records["done"] is False:
            nextRecordsUrl = first_records["nextRecordsUrl"]
            get_more_records(instance_url, headers, nextRecordsUrl, frames)

        print(f"All records retrieved for {query_name}, combining")
        df = pd.concat(frames)
        # drop empty columns
        df = df.dropna(axis=1, how='all')

        # rename the columns using labels in queries.json
        if query.get("column_mappings") is not None:
            df.rename(columns=query["column_mappings"], inplace=True)

        # t1 and t2 fields annoyingly use ids instead of names
        # this was the hacky workaround until a SOQL solution was found
        # if query_name == "Cases":
        #     replace_ids_with_names(instance_url,
        #                            headers,
        #                            df,
        #                            ["Tier 1 Diagnosed By",
        #                             "Tier 2 Analysis Done by"])

        save_data(query_name, df)

    input("Done!")
    os.remove("token.json")


main()
