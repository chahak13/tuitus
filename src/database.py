import os

import pandas as pd
import requests
from py2neo import Graph, Node, Relationship
from tqdm import tqdm

tuitus_db = Graph("bolt://localhost:7687", user="neo4j", password="tuitusci")


def summarize_csv(filepath):
    """
    Summarize a CSV

    This function generates a dictionary that contains the summary
    of the CSV. It also performs some preprocessing on the column
    names by stripping off any whitespace before and after the column
    name and converting the column name to a snake-case. Furthermore,
    it also adds an "increment_<column_name>" key to the summary that
    records the increments used in the first column of the CSV.
    """
    extension = os.path.splitext(filepath)[1].lower()
    if extension == ".csv":
        df = pd.read_csv(filepath)
    elif extension == ".txt":
        df = pd.read_csv(filepath, engine="python", sep=None)
    else:
        return None, dict()
    df.columns = (
        df.columns.str.strip().str.replace("\s+", "", regex=True).str.lower()
    )
    summary = df.describe(include="all").round(2).to_dict()
    summary = {
        colname: colsummary
        for colname, colsummary in summary.items()
        for k, v in colsummary.items()
        if not pd.isna(v)
    }
    for colname, colsummary in summary.items():
        for k, v in colsummary.items():
            try:
                colsummary[k] = v.item()
            except AttributeError:
                pass
    increment = (
        (df[df.columns[0]].iloc[2] - df[df.columns[0]].iloc[1]).round(5).item()
    )
    summary[f"increment_{df.columns[0]}"] = increment
    return df, summary


def _create_or_return_node(node_type, node_key, graphdb, **node_props):
    matching = graphdb.nodes.match(node_type, **node_props)
    if len(matching) == 0:
        node = Node(node_type, **node_props)
        graphdb.create(node)
    else:
        node = list(matching)[0]
    return node


def _create_or_return_rel(node1, node2, r_type, graphdb):
    matching = graphdb.relationships.match(nodes=(node1, node2), r_type=r_type)
    if len(matching) == 0:
        rel = Relationship(node1, r_type, node2)
        graphdb.create(rel)
    else:
        rel = list(matching)[0]
    return rel


def create_project_graph(project_info, project_path, graphdb):
    project_id = project_info.get("project_id", None)
    if project_id is None:
        project_id = project_info.get("projectId", None)
    if project_id is None:
        raise KeyError("project_id or projectId not found in project info.")

    project_props = {"name": project_id}
    project_node = _create_or_return_node(
        "Project", {"name": project_id}, graphdb, **project_props
    )

    pi = project_info["project"]["value"]["pi"]
    pi_props = {"name": pi}
    pi_node = _create_or_return_node(
        "Author", {"name": pi}, graphdb, **pi_props
    )
    pi_project_rel = Relationship(pi_node, "SUPERVISES", project_node)
    graphdb.create(pi_project_rel)

    for nh in project_info["project"]["value"].get("nhTypes", []):
        nh_props = {"name": nh}
        nh_node = _create_or_return_node(
            "Hazard", nh_props, graphdb, **nh_props
        )
        _create_or_return_rel(project_node, nh_node, "NATURAL_HAZARD", graphdb)

    project_type = _create_or_return_node(
        "PROJECT_TYPE",
        {"name": "experimental"},
        graphdb,
        **{"name": "experimental"},
    )
    _create_or_return_rel(project_node, project_type, "TYPE", graphdb)
    for exp in tqdm(
        project_info["experimentsList"], desc="Experiment", leave=False
    ):
        experiment_props = {
            "uuid": exp["uuid"],
            "title": exp["value"]["title"],
        }
        exp_node = _create_or_return_node(
            "Experiment", {"uuid": exp["uuid"]}, graphdb, **experiment_props
        )
        _ = _create_or_return_rel(
            project_node, exp_node, "HAS_EXPERIMENT", graphdb
        )

    for model in tqdm(project_info["modelConfigs"], desc="Model", leave=False):
        model_props = {
            "uuid": model["uuid"],
            "title": model["value"]["title"],
        }
        model_node = _create_or_return_node(
            "Model", {"uuid": model["uuid"]}, graphdb, **model_props
        )
        model_exps = model["value"]["experiments"]
        for exp_uuid in model_exps:
            exp_matching = graphdb.nodes.match("Experiment", uuid=exp_uuid)
            if len(exp_matching) > 0:
                exp_node = list(exp_matching)[0]
                _ = _create_or_return_rel(
                    exp_node, model_node, "HAS_MODEL", graphdb
                )

    for event in tqdm(project_info["eventsList"], desc="Events", leave=False):
        event_props = {
            "title": event["value"]["title"],
        }
        event_node = _create_or_return_node(
            "Event", {"title": event_props["title"]}, graphdb, **event_props
        )
        event_exps = event["value"]["experiments"]
        for exp_uuid in event_exps:
            exp_matching = graphdb.nodes.match("Experiment", uuid=exp_uuid)
            if len(exp_matching) > 0:
                exp_node = list(exp_matching)[0]
                _ = _create_or_return_rel(
                    exp_node, event_node, "HAS_EVENT", graphdb
                )

        event_models = event["value"]["modelConfigs"]
        for model_uuid in event_models:
            model_matching = graphdb.nodes.match("Model", uuid=model_uuid)
            if len(model_matching) > 0:
                model_node = list(model_matching)[0]
                event_model_rel = Relationship(
                    model_node, "HAS_EVENT", event_node
                )
                graphdb.create(event_model_rel)
                _create_or_return_rel(
                    model_node, event_node, "HAS_EVENT", graphdb
                )

        for fdict in event["fileObjs"]:
            f = fdict["path"][1:]
            # extension = os.path.splitext(f)[1].lower()
            # if extension not in {".txt", ".csv"}:
            #     continue
            filepath = os.path.join(project_path, project_id, f)
            file_node = _create_or_return_node(
                "File",
                {"filepath": filepath},
                graphdb,
                **{"filepath": filepath},
            )
            _ = _create_or_return_rel(
                event_node, file_node, "HAS_FILE", graphdb
            )
            _, summary = summarize_csv(filepath)
            for key, props in summary.items():
                if not isinstance(props, dict):
                    props = {key: props}
                col_props = {"name": key, **props}
                column_node = _create_or_return_node(
                    "Data", {"name": key}, graphdb, **col_props
                )
                _ = _create_or_return_rel(
                    project_node, column_node, "RECORDS", graphdb
                )
                _ = _create_or_return_rel(
                    event_node, column_node, "RECORDS", graphdb
                )
                _ = _create_or_return_rel(
                    file_node, column_node, "RECORDS", graphdb
                )
    return


for projectId in tqdm(["PRJ-3484", "PRJ-2136", "PRJ-2557"], desc="Project"):
    # projectId = "PRJ-3484"
    url = f"https://designsafe-ci.org/api/projects/publication/{projectId}"

    payload = ""
    headers = {}

    response = requests.request("GET", url, data=payload, headers=headers)
    response_json = response.json()

    create_project_graph(response_json, "../test/", tuitus_db)
    # break
