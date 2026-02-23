import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# Initialize session state
if 'graph' not in st.session_state:
    st.session_state['graph'] = None
if 'nodes1' not in st.session_state:
    st.session_state['nodes1'] = []
if 'nodes2' not in st.session_state:
    st.session_state['nodes2'] = []

# Path to the Excel file
file_path= "Idea-Triggers-Tools_T.xlsx"

# Read the Excel file
df = pd.read_excel(file_path)

st.header("INNOVENTOR :: unleash your creative self!")
# st.header("Unleash your creative self!")
st.subheader("Problem Space: Formulation")
st.markdown("<hr style='border: 2px solid red;'>", unsafe_allow_html=True)
st.text_area("Enter the Brief Problem Description:")
# Create two columns with specified width ratios
col1, col2 = st.columns([2, 2])  # Adjust the ratios as needed
with col1:
    st.write("Substance-Function Diagram Creator")
    central_node1 = st.text_input("**Enter S1(Control Object - Internal) :**", value="", key="central_node1",
                                  help="Enter object which are in design scope.")
    central_node2 = st.text_input("**Enter S2(Working Element - External) :**", value="", key="central_node2",
                                  help="Enter working element from customer side.")
    connected_nodes1 = st.text_input("**Enter Connected Nodes for S1 (comma-separated):**", value="",
                                     key="connected_nodes1",
                                     help="Enter the connected nodes to S1, separated by commas.")
    connected_nodes2 = st.text_input("**Enter Connected Nodes for S2 (comma-separated):**", value="",
                                     key="connected_nodes2",
                                     help="Enter the connected nodes to S2, separated by commas.")
# Customer CSS for buttons
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: #007BFF !important;
            color: white !important;
            padding: 15px 40px !important;
            font-size: 40px !important;
            border: none !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            white-space: nowrap
        }
        div.stButton > button:first-child:hover {
            background-color: #0056b3 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("Create Nodal"):
        #st.balloons()  # Add balloons effect
        if central_node1 and central_node2 and connected_nodes1 and connected_nodes2:
            # Create a graph
            G = nx.Graph()

         # Add central nodes
            G.add_node(central_node1)
            G.add_node(central_node2)

            # Add connected nodes for the first central node
            st.session_state['nodes1'] = connected_nodes1.split(',')
            for node in st.session_state['nodes1']:
                G.add_node(node.strip())
                G.add_edge(central_node1, node.strip())
                selected_node = []

            # Add connected nodes for the second central node
            st.session_state['nodes2'] = connected_nodes2.split(',')
            for node in st.session_state['nodes2']:
                G.add_node(node.strip())
                G.add_edge(central_node2, node.strip())

            # Connect the two central nodes
            G.add_edge(central_node1, central_node2)

            # Store the graph in session state
            st.session_state['graph'] = G

with col2:
    # Draw the graph if it exists in session state
    if st.session_state['graph'] is not None:
        G = st.session_state['graph']
        pos = nx.spring_layout(G)
        plt.figure(figsize=(10, 8))

        # Draw nodes with different colors and increased sizes
        nx.draw_networkx_nodes(G, pos, nodelist=[central_node1, central_node2], node_color='orange', node_size=3000)
        nx.draw_networkx_nodes(G, pos,
                               nodelist=[node.strip() for node in st.session_state['nodes1']] + [node.strip() for node
                                                                                                 in st.session_state[
                                                                                                     'nodes2']],
                               node_color='skyblue', node_size=2500)
        nx.draw_networkx_edges(G, pos, edge_color='gray')
        nx.draw_networkx_labels(G, pos, font_size=16, font_color='black')

        st.pyplot(plt)

        with col1:
            st.write("#### Analyze Functions & Define Trade-Off")
            DesiredWE = st.text_area("Describe Desired WE State & Condition")
            Func_para = st.text_area(
                "Enter all standalone Desired Functions to achieve Desired WE state (form: coil heats water)-Refer Diagram Cn")
            MUF_para = st.text_input("Enter MUF parameter & Unit")
            Prob_Condn = st.text_input("Conditions & Frequency for MUF ")
            UDF_para = st.text_area("Enter Standalone Undesired Functions & Unit")
            UDF_Condn = st.text_input("Conditions & Frequency for UDF ")
        with col2:
            st.write("#### Unconstraint Ideation")
            st.markdown("**IFR-I: Working Element achieves end state (as desired by system's function) all by Itself**")
            st.text_area("IFR1:")
            st.markdown("**IFR-II: Target component performs all the functions of system and adjacent components**")
            st.text_area("IFR2:")
            st.markdown("**Enter an Unconstrained yet specific solution**")
            unconstrained_solution = st.text_area("Unconstrained Solution:")

            st.markdown("**Enter corresponding microfunction**")
            microfun = st.text_input("microfunction:")
            st.markdown("**Enter Base Solution Elements (ENIGMA)**")
            SolnDim = st.text_input("GEMI-Space-Time Elements:")
            Resources = st.text_area("Enter internal & external Resources with their Derivatives:")

st.markdown("<hr style='border: 2px solid red;'>", unsafe_allow_html=True)
 # For nodes1 checkboxes with input boxes


# Create two columns for the buttons

node1 = st.session_state.get('nodes1', [])
node2 = st.session_state.get('nodes2', [])
nodeC1 = st.session_state.get('central_node1', "")
nodeC2 = st.session_state.get('central_node2', "")

selected_nodes1 = []
node1_inputs = {}

# Ensure central nodes are lists
if not isinstance(nodeC1, list):
        nodeC1 = [nodeC1]
if not isinstance(nodeC2, list):
        nodeC2 = [nodeC2]
nodes = node1 + nodeC1 + node2 + nodeC2
col1, col2 = st.columns(2)
with col1:
    GoDE = st.checkbox("Enhance Desired Effect")

with col2:
    Go2 = st.checkbox("Elliminate Undesired Effect")


if GoDE:
    node1 = st.session_state.get('nodes1', [])
    node2 = st.session_state.get('nodes2', [])
    nodeC1 = st.session_state.get('central_node1', [])
    nodeC2 = st.session_state.get('central_node2', [])

    # Ensure central nodes are lists
    if not isinstance(nodeC1, list):
        nodeC1 = [nodeC1]
    if not isinstance(nodeC2, list):
        nodeC2 = [nodeC2]

    # Combine all nodes
    nodes = node1 + nodeC1 + node2 + nodeC2

    # Initialize containers for selected nodes and inputs
    selected_nodes1 = []
    node1_inputs = {}

    # Iterate through the combined node list
    for idx, node in enumerate(nodes):
        col1, col2 = st.columns([1, 2])
        with col1:
            checked = st.checkbox(node.strip(), key=f"checkbox_nodes1_{idx}")
        with col2:
            user_input = st.text_input(f"Desired State Of {node.strip()}", key=f"input_nodes1_{idx}")

        if checked:
            selected_nodes1.append(node.strip())
            node1_inputs[node.strip()] = user_input


    # Display popup at bottom with selected inputs
    if selected_nodes1:
        popup_content = ""
        for node in selected_nodes1:
            input_value = node1_inputs.get(node, "")
            popup_content += f"<p>{node}: {input_value}</p>"
        # Desired State PopUp
        st.markdown(
            f"""
            <style>
            .popup-center {{
                position: fixed;
                top: 12%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #008880;
                color: #ffffff;
                border: 2px solid #ffe6f0;
                padding: 10px;
                border-radius: 12px;
                width: 50%;
                z-index: 9999;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                text-align: center;
                font-size: 20px;
            }}
            </style>
            <div class="popup-center">
                <strong> {popup_content}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )

# Su Field Operators

        # Initialize counters
        if "counter2" not in st.session_state:
            st.session_state.counter2 = 0
        if "counter" not in st.session_state:
            st.session_state.counter = 0

    # Background colors for popup
popup_colors = ["#fff3f3", "#f0f8ff", "#e6ffe6", "#fffbe6",
                    "#f9f0ff", "#e6f7ff", "#ffe6f0", "#f0fff0"]
if Go2:
            st.write("#### Eliminate Undesired Effects")
            UDE = st.text_area("Describe Undesired State / Effect / Function : UDE", key="ude_input")

            st.write("Click Two interacting objects which produce the above UDE")
            st.markdown(
                "<h5 style='color:red;'>Apply IFR: Use or Modify Cause ITSELF to eliminate undesired effect</h5>",
                unsafe_allow_html=True
            )

            selected_nodes1 = []

            node1 = st.session_state.get('nodes1', [])
            node2 = st.session_state.get('nodes2', [])
            nodeC1 = st.session_state.get('central_node1', "")
            nodeC2 = st.session_state.get('central_node2', "")

            # Ensure central nodes are lists
            nodeC1 = [nodeC1] if not isinstance(nodeC1, list) else nodeC1
            nodeC2 = [nodeC2] if not isinstance(nodeC2, list) else nodeC2

            nodes = node1 + nodeC1 + node2 + nodeC2
            cols = st.columns(len(nodes))

            for idx, (col, node) in enumerate(zip(cols, nodes)):
                key = f"checkbox_nodes1_{idx}_{node.strip()}"
                with col:
                    checked = st.checkbox(node.strip(), key=key)
                    if checked:
                        selected_nodes1.append(node.strip())

            if selected_nodes1:
                st.success(f"Apply Ideation Operators for Selected nodes: {selected_nodes1}")
# Initialize session state for the input field
if "ideas" not in st.session_state:
        st.session_state.ideas = ""

# Checkbox to clear the input
# Su-Field button
if st.button("Su-Field-Ideator"):
    st.session_state.counter2 = st.session_state.get("counter2", 0) + 1
    if st.session_state.counter2 > 8:
        st.session_state.counter2 = 1

    if st.session_state.counter2 > 0:
        i = st.session_state.counter2 - 1
        operator = df.iloc[i, 3]
        control = df.iloc[i, 4]
        bg_color = popup_colors[i % len(popup_colors)]

        st.markdown(
            f"""
                            <style>
                            .popup {{
                                position: fixed;
                                left: 50%;
                                transform: translateX(-50%);
                                background-color: {bg_color};
                                border: 3px solid #FFF0FF;
                                padding: 10px;
                                border-radius: 12px;
                                z-index: 9999;
                                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                                font-size: 20px;
                                width: 50%;
                                text-align: center;
                            }}
                            .popup-operator {{
                                top: 16%;
                            }}
                            .popup-control {{
                                top: 27%;
                            }}
                            </style>

                            <div class="popup popup-operator">
                                <strong>⭐ Operator:</strong><br>{operator}
                            </div>

                            <div class="popup popup-control">
                                <strong>🎛️ Control:</strong><br>{control}
                            </div>
                            """,
            unsafe_allow_html=True
        )
if st.checkbox("🔁Clear"):
    st.session_state.ideas = ""  # This clears the input field

file_name = st.text_input("Enter .csv file name to store ideas (without extension):", "ideas")
ideas = st.text_input("Record Your Creative Ideas:", value=st.session_state.ideas, key="ideas")
# Text input for the CSV file name

    # Record Ideas button
# Text area for entering the idea
#ideas = st.text_area("💡 Enter your idea here:")

# Button to save the idea
if st.button("🚀 Record-ideas"):
    if file_name.strip() == "":
        st.warning("⚠️ Please enter a valid file name.")
    else:
        csv_file = f"{file_name.strip()}.csv"
        df_idea = pd.DataFrame([[ideas]], columns=["Ideas"])
        if os.path.exists(csv_file):
            df_idea.to_csv(csv_file, mode='a', header=False, index=False)
        else:
            df_idea.to_csv(csv_file, index=False)
        st.toast("✅ Your idea has been saved!")

# Random Idea Trigger
if st.button("✨ Random-Idea-Triggers"):
    st.session_state.counter += 1
    random_integer_np = np.random.randint(0, 37)
    st.markdown(
        f"""
        <div style="border: 2px solid orange; padding: 10px; border-radius: 5px;">
            <p>{df.iloc[random_integer_np, 1]}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.write(
        f"Remember Inventors: Form of the solution may completely change with every new Idea! Count: {st.session_state.counter}")



