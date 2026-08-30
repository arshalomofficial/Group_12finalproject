import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import plotly.express as px
import folium

OUT = "outputs"
os.makedirs(OUT, exist_ok=True)


def heading(t):
    print("\n" + "=" * 55)
    print(t)
    print("=" * 55)


# ── Task 1: Load ─────────────────────────────────────────────
heading("TASK 1: LOADING THE DATASETS")

utilities   = pd.read_csv("utilities.csv")
substations = pd.read_csv("substations.csv")
lines       = pd.read_csv("lines.csv")

print("utilities   :", utilities.shape)
print("substations :", substations.shape)
print("lines       :", lines.shape)
print("\nColumns:", list(substations.columns))
print("\nFirst 3 substations:\n", substations.head(3).to_string())


# ── Task 2: Clean ────────────────────────────────────────────
heading("TASK 2: CLEANING")

print("Missing values - utilities:\n",    utilities.isnull().sum().to_string())
print("\nMissing values - substations:\n", substations.isnull().sum().to_string())
print("\nMissing values - lines:\n",       lines.isnull().sum().to_string())

for col in ["Latitude", "Longitude", "Capacity (MVA)", "Voltage (kV)"]:
    substations[col] = pd.to_numeric(substations[col], errors="coerce")
for col in ["Length (km)", "Capacity (MVA)"]:
    lines[col] = pd.to_numeric(lines[col], errors="coerce")

print("\nDuplicates - utilities:",    utilities.duplicated().sum())
print("Duplicates - substations:", substations.duplicated().sum())
print("Duplicates - lines:",        lines.duplicated().sum())

utilities   = utilities.drop_duplicates()
substations = substations.drop_duplicates()
lines       = lines.drop_duplicates()

valid_ids   = set(substations["Substation ID"])
orphan_mask = (
    ~lines["Source Substation ID"].isin(valid_ids) |
    ~lines["Destination Substation ID"].isin(valid_ids)
)
print(f"\nOrphaned lines: {orphan_mask.sum()}")
lines = lines[~orphan_mask].reset_index(drop=True)

# extended to -16 longitude to include the Guinea cross-border node
bad_coords = substations[
    (substations["Latitude"]  <  -5) | (substations["Latitude"]  > 16) |
    (substations["Longitude"] < -16) | (substations["Longitude"] >  3)
]
print(f"Bad coordinate rows: {len(bad_coords)}")
if len(bad_coords):
    print(bad_coords[["Name", "Latitude", "Longitude"]])

print("\nClean substations:", substations.shape)
print("Clean lines:", lines.shape)


# ── Task 3: EDA ──────────────────────────────────────────────
heading("TASK 3: EDA")

print(substations["Region"].value_counts().to_string())
print("\nVoltage levels (kV):\n", substations["Voltage (kV)"].value_counts().sort_index().to_string())
print("\nSubstation status:\n",   substations["Status"].value_counts().to_string())
print("\nLine status:\n",         lines["Status"].value_counts().to_string())
print("\nLine type:\n",           lines["Line Type"].value_counts().to_string())
print("\nNumeric summary:\n",
      substations[["Voltage (kV)", "Capacity (MVA)", "Commissioning Year"]].describe().to_string())

plt.figure(figsize=(10, 5))
substations["Region"].value_counts().plot(kind="bar", color="steelblue", edgecolor="white")
plt.title("Substations per Region")
plt.xlabel("Region")
plt.ylabel("Count")
plt.xticks(rotation=40, ha="right")
plt.tight_layout()
plt.savefig(f"{OUT}/eda_substations_per_region.png", dpi=130)
plt.close()

plt.figure(figsize=(7, 4))
substations["Voltage (kV)"].value_counts().sort_index().plot(
    kind="bar", color="darkorange", edgecolor="white")
plt.title("Voltage Level Distribution")
plt.xlabel("Voltage (kV)")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(f"{OUT}/eda_voltage_levels.png", dpi=130)
plt.close()

all_ep = pd.concat([lines["Source Substation"], lines["Destination Substation"]])
plt.figure(figsize=(10, 5))
all_ep.value_counts().head(10).plot(kind="bar", color="seagreen", edgecolor="white")
plt.title("Top 10 Substations by Connected Lines")
plt.xlabel("Substation")
plt.ylabel("Line Count")
plt.xticks(rotation=40, ha="right")
plt.tight_layout()
plt.savefig(f"{OUT}/eda_top_substations.png", dpi=130)
plt.close()

plt.figure(figsize=(9, 5))
substations["Commissioning Year"].dropna().astype(int).plot(
    kind="hist", bins=15, color="mediumpurple", edgecolor="white", alpha=0.8)
plt.title("Commissioning Year Distribution")
plt.xlabel("Year")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(f"{OUT}/eda_commissioning_years.png", dpi=130)
plt.close()

print(f"\n4 charts saved to {OUT}/")


# ── Task 4: Merge and business intelligence ──────────────────
heading("TASK 4: MERGING")

lm = lines.merge(
    substations[["Substation ID", "Name", "Region", "Country"]],
    left_on="Source Substation ID", right_on="Substation ID", how="left"
).rename(columns={"Name": "Name_source", "Region": "Region_source", "Country": "Country_source"})

lm = lm.merge(
    substations[["Substation ID", "Name", "Region", "Country"]],
    left_on="Destination Substation ID", right_on="Substation ID",
    how="left", suffixes=("_src", "_dest")
).rename(columns={"Name": "Name_dest", "Region": "Region_dest", "Country": "Country_dest"})

lm = lm.merge(
    utilities[["Utility ID", "Name", "Code"]],
    on="Utility ID", how="left"
).rename(columns={"Name": "Utility_Name"})

print("Merged shape:", lm.shape)
print(lm[["Code", "Source Substation", "Region_source",
          "Destination Substation", "Region_dest"]].head().to_string())

by_util = (
    lm.groupby(["Code", "Region_source"])
    .size().reset_index(name="Line Count")
    .sort_values("Line Count", ascending=False)
)
print("\nTop 10 utility/region combos:")
print(by_util.head(10).to_string(index=False))

top10 = by_util.head(10)
plt.figure(figsize=(12, 5))
plt.bar(top10["Code"] + " - " + top10["Region_source"],
        top10["Line Count"], color="teal", edgecolor="white")
plt.title("Top 10 Utility/Region Combos by Line Count")
plt.xlabel("Utility - Region")
plt.ylabel("Lines")
plt.xticks(rotation=40, ha="right")
plt.tight_layout()
plt.savefig(f"{OUT}/utility_region_lines.png", dpi=130)
plt.close()

lm.to_csv(f"{OUT}/merged_lines.csv", index=False)
print(f"Saved to {OUT}/merged_lines.csv")


# ── Task 5: Network analysis ─────────────────────────────────
heading("TASK 5: NETWORK ANALYSIS")

G = nx.Graph()
for _, sub in substations.iterrows():
    G.add_node(sub["Short Name"],
               region=sub["Region"], voltage=sub["Voltage (kV)"],
               capacity=sub["Capacity (MVA)"], lat=sub["Latitude"],
               lon=sub["Longitude"], status=sub["Status"])

full_to_short = dict(zip(substations["Name"], substations["Short Name"]))
for _, line in lines.iterrows():
    src = full_to_short.get(line["Source Substation"])
    dst = full_to_short.get(line["Destination Substation"])
    if src and dst and src in G and dst in G:
        G.add_edge(src, dst, length_km=line["Length (km)"],
                   voltage=line["Voltage (kV)"], status=line["Status"])

print(f"Nodes: {G.number_of_nodes()}   Edges: {G.number_of_edges()}")
print(f"Connected: {nx.is_connected(G)}   Components: {nx.number_connected_components(G)}")

deg = nx.degree_centrality(G)
bet = nx.betweenness_centrality(G)
clo = nx.closeness_centrality(G)
pgr = nx.pagerank(G, alpha=0.85)
clu = nx.clustering(G)
avg_clu = sum(clu.values()) / len(clu)


def show_top10(d, label):
    ranked = sorted(d.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\nTop 10 — {label}:")
    for n, s in ranked:
        print(f"  {n:<35} {s:.4f}")
    return ranked


top_deg = show_top10(deg, "Degree Centrality")
top_bet = show_top10(bet, "Betweenness Centrality")
top_clo = show_top10(clo, "Closeness Centrality")
top_pgr = show_top10(pgr, "PageRank")
print(f"\nAverage clustering coefficient: {avg_clu:.4f}")

if nx.is_connected(G):
    diam     = nx.diameter(G)
    avg_path = nx.average_shortest_path_length(G)
    print(f"Diameter: {diam}   Avg path length: {avg_path:.3f}")
else:
    lcc      = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    diam     = nx.diameter(lcc)
    avg_path = nx.average_shortest_path_length(lcc)
    print(f"Largest component: {lcc.number_of_nodes()} nodes")
    print(f"Diameter: {diam}   Avg path length: {avg_path:.3f}")

communities = nx.community.greedy_modularity_communities(G)
print(f"\nCommunities found: {len(communities)}")
for i, c in enumerate(communities):
    print(f"  {i+1} ({len(c)} nodes): {sorted(c)[:4]} ...")

bridges = list(nx.bridges(G))
print(f"\nBridge lines (removing one disconnects the network): {len(bridges)}")
for u, v in bridges[:8]:
    print(f"  {u} -- {v}")

top_hub = top_deg[0][0]
before  = nx.number_connected_components(G)
Gt      = G.copy()
Gt.remove_node(top_hub)
after   = nx.number_connected_components(Gt)
print(f"\nN-1: remove '{top_hub}' => {before} -> {after} components")
print("  Network splits — resilience concern." if after > before else "  Network stays connected.")

top_bw = top_bet[0][0]
if top_bw != top_hub:
    Gt2  = G.copy()
    Gt2.remove_node(top_bw)
    cc2  = nx.number_connected_components(Gt2)
    print(f"\nN-1: remove betweenness node '{top_bw}' => {before} -> {cc2} components")

# static network diagram
plt.figure(figsize=(14, 10))
pos     = nx.spring_layout(G, seed=42)
regions = list({G.nodes[n].get("region", "?") for n in G.nodes})
rcol    = {r: plt.cm.tab20(i / max(len(regions), 1)) for i, r in enumerate(regions)}
colours = [rcol.get(G.nodes[n].get("region", "?"), "gray") for n in G.nodes]
nx.draw_networkx_nodes(G, pos, node_color=colours, node_size=200, alpha=0.9)
nx.draw_networkx_labels(G, pos, font_size=6)
nx.draw_networkx_edges(G, pos, edge_color="gray", alpha=0.5, width=1)
plt.title("National Grid Network — nodes coloured by region")
plt.axis("off")
plt.tight_layout()
plt.savefig(f"{OUT}/network_graph.png", dpi=150)
plt.close()

fig = px.scatter_geo(
    substations, lat="Latitude", lon="Longitude",
    hover_name="Name", color="Region", size="Capacity (MVA)", size_max=18,
    title="Substation Locations (bubble = capacity)", projection="natural earth",
)
fig.write_html(f"{OUT}/substation_map_plotly.html")

m = folium.Map(location=[7.9, -1.0], zoom_start=6)
slookup = substations.set_index("Substation ID")
vcol    = {11: "green", 33: "blue", 69: "orange", 161: "red", 330: "purple"}

for _, sub in substations.iterrows():
    kv  = int(sub["Voltage (kV)"]) if pd.notna(sub["Voltage (kV)"]) else 0
    folium.CircleMarker(
        location=[sub["Latitude"], sub["Longitude"]],
        popup=(f"<b>{sub['Name']}</b><br>Region: {sub['Region']}<br>"
               f"{kv} kV | {sub['Capacity (MVA)']} MVA | {sub['Status']}"),
        radius=5, color=vcol.get(kv, "gray"), fill=True, fill_opacity=0.8,
    ).add_to(m)

for _, line in lines.iterrows():
    try:
        src = slookup.loc[line["Source Substation ID"]]
        dst = slookup.loc[line["Destination Substation ID"]]
        lc  = "red" if line["Status"] == "Under Maintenance" else "gray"
        folium.PolyLine(
            locations=[[src["Latitude"], src["Longitude"]],
                       [dst["Latitude"], dst["Longitude"]]],
            weight=2, color=lc, opacity=0.6,
            tooltip=f"{line['Source Substation']} to {line['Destination Substation']}",
        ).add_to(m)
    except KeyError:
        continue

m.save(f"{OUT}/grid_map_folium.html")
print(f"\nAll maps saved to {OUT}/")

# summary file
top_region  = substations["Region"].value_counts().idxmax()
top_voltage = int(substations["Voltage (kV)"].value_counts().idxmax())
active_pct  = (substations["Status"] == "Active").mean() * 100
maint_pct   = (lines["Status"] == "Under Maintenance").mean() * 100

summary = f"""GRID ANALYSIS - KEY FINDINGS
==============================
Dataset: {len(utilities)} utilities, {len(substations)} substations, {len(lines)} lines

EDA
  Most substations region : {top_region}
  Most common voltage     : {top_voltage} kV
  Active substations      : {active_pct:.1f}%
  Lines under maintenance : {maint_pct:.1f}%

NETWORK
  Nodes / Edges  : {G.number_of_nodes()} / {G.number_of_edges()}
  Components     : {nx.number_connected_components(G)}
  Avg clustering : {avg_clu:.4f}
  Diameter       : {diam}
  Avg path len   : {avg_path:.3f}
  Communities    : {len(communities)}
  Bridge lines   : {len(bridges)}

TOP NODES
  Degree      : {top_deg[0][0]} ({top_deg[0][1]:.4f})
  Betweenness : {top_bet[0][0]} ({top_bet[0][1]:.4f})
  Closeness   : {top_clo[0][0]} ({top_clo[0][1]:.4f})
  PageRank    : {top_pgr[0][0]} ({top_pgr[0][1]:.4f})

N-1: remove '{top_hub}': {before} -> {after} components
     {'Fragments' if after > before else 'Stays connected'}

NOTE: all data is synthetic - not real Ghana grid values.
Centrality scores are structural proxies only.
"""

with open(f"{OUT}/findings_summary.txt", "w") as f:
    f.write(summary)

print(summary)
print(f"Done. All outputs in {OUT}/")
