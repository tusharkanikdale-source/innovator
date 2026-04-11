import os
import time
import csv
import io
import random
from tempfile import NamedTemporaryFile

import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

st.set_page_config(page_title="Professional Su-Field i-board", layout="wide")

# Initialize Session States
if "canvas_ids" not in st.session_state:
    st.session_state.canvas_ids = [1]  # Track active internal canvas IDs dynamically
if "next_canvas_id" not in st.session_state:
    st.session_state.next_canvas_id = 2 # Track the next internal ID to assign

if "prev_color" not in st.session_state:
    st.session_state.prev_color = "Default (Black)"

# --- Idea Recorder States ---
if "ideas" not in st.session_state:
    st.session_state.ideas = []

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.subheader("🎨 Component Styling")
    
    node_category = st.radio(
        "Outline Color", 
        options=[
            "Default (Black)", 
            "Desired (Green)", 
            "Undesired (Red)", 
            "External (Blue)",
            "Special (Purple)" 
        ],
        help="Select a shape on the i-board and click a color here to change it. Also sets the default color for new shapes."
    )
   
    color_changed = (st.session_state.prev_color != node_category)
    st.session_state.prev_color = node_category
    
    st.markdown("---")
    st.subheader("🔍 View Controls")
    
    # Track zoom and view states securely across reruns
    if "view_scale" not in st.session_state:
        st.session_state.view_scale = 1.0
    if "action_zoom" not in st.session_state:
        st.session_state.action_zoom = None
    if "zoom_slider" not in st.session_state:
        st.session_state.zoom_slider = 1.0 # Initialize widget key explicitly
        
    def handle_zoom_change():
        st.session_state.view_scale = st.session_state.zoom_slider
        st.session_state.action_zoom = "zoom"

    def reset_zoom():
        st.session_state.zoom_slider = 1.0
        st.session_state.view_scale = 1.0
        st.session_state.action_zoom = "reset"

    st.slider(
        "Zoom Level (Left: Out | Right: In)", 
        min_value=0.1, 
        max_value=5.0, 
        step=0.1, 
        key="zoom_slider", 
        on_change=handle_zoom_change
    )

    st.button("🔲 Reset View", use_container_width=True, help="Center the diagram to its original size and position.", on_click=reset_zoom)
        
    js_action_zoom = f"'{st.session_state.action_zoom}'" if st.session_state.action_zoom else "null"
    js_view_scale = st.session_state.view_scale
    st.session_state.action_zoom = None  
    
    st.markdown("---")
    st.subheader("⚙️ Global i-board Settings")
    auto_create = st.toggle("Enable Auto-Creation Mode", value=True)
    directed = st.checkbox("Directed graph (arrows)", value=True)
    
    layout = st.selectbox(
        "Layout Style", 
        [
            "Force (Physics)", 
            "Force (Atlas 2 Clustering)", 
            "Force (Strict Repulsion)", 
            "Hierarchical"
        ], 
        index=0
    )
    
    if "Force" in layout:
        physics_enabled = st.checkbox("Enable floating physics", value=False)
    else:
        physics_enabled = False

    # --- Idea Management in Sidebar ---
    st.markdown("---")
    st.subheader("💡 Idea Management")
        
    if st.session_state.ideas:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Idea"])
        for idea in st.session_state.ideas:
            writer.writerow([idea["Timestamp"], idea["Idea"]])
        
        st.download_button(
            label="Download Ideas (.CSV)",
            data=output.getvalue(),
            file_name="canvas_ideas.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )
    else:
        st.info("No ideas recorded yet. Add them below the i-board!")

# -------------------- JAVASCRIPT VAR MAPPING --------------------
js_auto_create = "true" if auto_create else "false"
js_color_changed = "true" if color_changed else "false"
js_directed = "true" if directed else "false"

border_color_map = {
    "Default (Black)": "'#000000'",
    "Desired (Green)": "'#10B981'",
    "Undesired (Red)": "'#EF4444'",
    "External (Blue)": "'#3B82F6'",
    "Special (Purple)": "'#A855F7'" 
}
js_default_border = border_color_map[node_category]

# -------------------- HEADER --------------------
col_logo, col_title, col_help = st.columns([0.09, 0.77, 0.15])

with col_logo:
    try:
        st.image("icon_5.png", use_container_width=True)
    except:
        st.markdown("<div style='font-size: 40px; text-align: center;'>⚛️</div>", unsafe_allow_html=True)

with col_title:
    st.markdown("<h1 style='font-size: 30px; margin-top: 5px;'>Think  .Tinker .Transform</h1>", unsafe_allow_html=True)

with col_help:
    st.write("") 
    with st.popover("❓ Help", use_container_width=True):
        st.markdown(
            """
            **i-board Controls:**
            * **Left Click (Empty Space):** Add Node.
            * **Right Click (i-board):** Reset Tool / Enable Edge Mode.
            * **Double-Click (Node):** Instantly edit the State of the Object or Note.
            * **Shift + Left Click (Note/Data Point):** Randomly change its color!
            * **Ctrl + Click (Nodes):** Select multiple shapes to move or delete together.
            * **Ctrl + Left Drag:** Draw a zone to Copy shapes.
            * **Click '+' Dot:** Expand/Collapse hidden IFR/Par Sticky Note.
            * **Change Colors:** Click to select a node, then choose a color from the left panel!
            """
        )

# -------------------- RENDER FUNCTION FOR TABS --------------------
def render_canvas(tab_id, display_num):
    
    js_clear_board = "false"
    clear_stamp = "" 
    
    if display_num != 1:
        col_spacer, col_clear, col_del = st.columns([0.70, 0.15, 0.15])
        with col_clear:
            if st.button("🧹 Clear i-board", key=f"clear_btn_{tab_id}", use_container_width=True):
                js_clear_board = "true"
                clear_stamp = f"// Force iframe reload stamp: {time.time()}"
                
        with col_del:
            if st.button("🗑️ Delete i-board", key=f"del_btn_{tab_id}", type="secondary", use_container_width=True):
                st.session_state[f"confirm_delete_{tab_id}"] = True

        if st.session_state.get(f"confirm_delete_{tab_id}", False):
            st.warning(f"⚠️ Are you sure you want to delete i-board {display_num}? This action cannot be undone.")
            col_yes, col_no = st.columns([0.2, 0.8])
            with col_yes:
                if st.button("✅ Yes, Delete", key=f"yes_del_{tab_id}", use_container_width=True):
                    st.session_state.canvas_ids.remove(int(tab_id))
                    st.session_state[f"confirm_delete_{tab_id}"] = False
                    st.rerun()
            with col_no:
                if st.button("❌ No, Cancel", key=f"no_del_{tab_id}"):
                    st.session_state[f"confirm_delete_{tab_id}"] = False
                    st.rerun()
    else:
        col_spacer, col_clear = st.columns([0.85, 0.15])
        with col_clear:
            if st.button("🧹 Clear i-board", key=f"clear_btn_{tab_id}", use_container_width=True):
                js_clear_board = "true"
                clear_stamp = f"// Force iframe reload stamp: {time.time()}"

    net = Network(
        height="650px", 
        width="100%", 
        directed=directed,
        bgcolor="#ffffff",
        font_color="#333333"
    )

    if layout == "Hierarchical":
        net.options.layout = {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed"}}
        net.toggle_physics(False)
    else:
        if layout == "Force (Atlas 2 Clustering)":
            net.force_atlas_2based(gravity=-50, spring_length=100)
        elif layout == "Force (Strict Repulsion)":
            net.repulsion(node_distance=150)
        else:
            net.barnes_hut()
        
        net.toggle_physics(physics_enabled)

    try:
        with NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
            net.save_graph(tmp_file.name)
            with open(tmp_file.name, "r", encoding="utf-8") as f:
                source_code = f.read()
                
        # --- CUSTOM CSS INJECTION ---
        custom_css = """
        <style>
        div.vis-network div.vis-manipulation { display: none !important; }

        #custom-toolbar {
            position: absolute; top: 0; left: 0; width: 100%; height: 50px;
            background: #f1f3f5; border-bottom: 1px solid #dee2e6; display: flex;
            align-items: center; justify-content: flex-start; gap: 10px;
            padding: 0 20px; box-sizing: border-box; z-index: 1000;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        #custom-toolbar .custom-btn {
            padding: 6px 12px; border-radius: 6px; background-color: #ffffff;
            border: 1px solid #ced4da; color: #495057; font-size: 14px;
            font-weight: 500; cursor: pointer; transition: all 0.2s ease;
            display: flex; align-items: center; gap: 6px;
        }
        #custom-toolbar .custom-btn:hover { background-color: #e9ecef; border-color: #adb5bd; }
        #custom-toolbar .custom-btn.active { background-color: #dee2e6; border-color: #adb5bd;}
        
        .ideation-box {
            position: absolute; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            backdrop-filter: blur(4px); color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif;
            font-weight: normal; display: flex; align-items: center; justify-content: center;
            text-align: center; padding: 20px; box-sizing: border-box; pointer-events: none;
            z-index: 10002; border: 2px solid rgba(255,255,255,0.4); overflow: visible;
        }
        
        .ideation-balloon {
            position: absolute; border-radius: 50%;
            background: var(--bg-gradient, radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.9), rgba(252, 211, 77, 0.9) 60%, rgba(245, 158, 11, 0.9)));
            box-shadow: 0 10px 20px rgba(0,0,0,0.15), inset 0 -5px 15px rgba(0,0,0,0.1);
            backdrop-filter: blur(2px); color: #000000; text-shadow: 1px 1px 3px rgba(255,255,255,0.8);
            font-family: 'Segoe UI', Arial, sans-serif; font-weight: normal; font-size: 13px;
            display: flex; align-items: center; justify-content: center; text-align: center;
            padding: 20px; box-sizing: border-box; pointer-events: none; z-index: 10005;
            border: 1px solid rgba(255,255,255,0.6); animation: fadeIn 0.5s ease-out; 
            transition: opacity 0.5s ease, visibility 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }

        .ideation-balloon b { font-size: 1.1em; text-transform: uppercase; margin-bottom: 4px; display: inline-block; }
        .ideation-balloon::after {
            content: ''; position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%);
            border-left: 6px solid transparent; border-right: 6px solid transparent;
            border-bottom: 12px solid var(--tail-color, rgba(245, 158, 11, 0.9));
        }

        #param-display-box {
            position: absolute; right: 20px; top: 160px; width: 180px;
            background: rgba(255, 255, 255, 0.95); border: 1px solid #ced4da;
            padding: 15px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; z-index: 10001;
            display: none; max-height: 80%; overflow-y: auto; color: #333;
        }
        #param-display-box h4 { margin: 0 0 8px 0; font-size: 10px; }
        #param-display-box ul { margin: 0 0 15px 0; padding-left: 20px; font-size: 13px; }
        #param-display-box li { margin-bottom: 5px; line-height: 1.4; }
        </style>
        """
                
        js_injection = """
        var autoCreateEnabled = """ + js_auto_create + """;
        var defaultBorder = """ + js_default_border + """;
        var triggerClearBoard = """ + js_clear_board + """;
        """ + clear_stamp + """
        var defaultBg = '#ffffff'; 
        window.isAddingResource = false;
        window.isAddingNode = false;
        window.isAddingIFR = false;
        window.isAddingPar = false;
        window.isAddingSoln = false;
        window.isAddingSticky = false; 
        window.isPasting = false;
        
        window.isIdeationActive = false;
        window.ideationBalloons = [];
        
        window.balloonToggleIntervalId = null;
        window.tempAddedNodes = []; 
        window.modifiedOriginalNodes = []; 
        window.ideationAnimationId = null;

        window.clearAllButtonStates = function() {
            var allBtns = document.querySelectorAll('#custom-toolbar .custom-btn');
            if (allBtns) allBtns.forEach(b => b.classList.remove('active'));
        };
        
        options.interaction = { zoomView: false, multiselect: true };

        options.nodes = {
            shape: 'dot', size: 30, borderWidth: 3, borderWidthSelected: 5,  
            color: { background: defaultBg, border: defaultBorder, highlight: { background: defaultBg, border: defaultBorder }, hover: { background: defaultBg, border: defaultBorder } },
            font: { size: 16, face: 'arial', vadjust: 5, color: defaultBorder }
        };

        options.edges = {
            arrows: { to: { enabled: """ + js_directed + """, scaleFactor: 0.5, type: 'arrow' } },
            color: { color: '#666666', highlight: '#333333', hover: '#333333' },
            width: 1, smooth: { type: 'continuous' }
        };
        
        options.manipulation = {
            enabled: true, initiallyActive: true,
            addNode: function(nodeData, callback) {
                // If Sol-Plot or Sticky is active, block native node creation entirely!
                if (window.isAddingSoln || window.isAddingSticky || window.isPasting) {
                    callback(null);
                    setTimeout(function() { network.disableEditMode(); }, 10);
                    return;
                }
            
                var isRes = window.isAddingResource;
                var label = prompt(isRes ? "Enter Resource Name:" : "Enter Object and its State:", isRes ? "New Resource" : "Object : State");
                
                window.isAddingResource = false; window.isAddingNode = false; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false;
                window.clearAllButtonStates();

                if (label !== null && label.trim() !== "") {
                    nodeData.label = label; nodeData.shape = isRes ? 'hexagon' : 'dot'; nodeData.size = isRes ? 15 : 30; 
                    nodeData.color = { background: defaultBg, border: defaultBorder, highlight: { background: defaultBg, border: defaultBorder }, hover: { background: defaultBg, border: defaultBorder } };
                    callback(nodeData);
                } else { callback(null); }
            },
            editNode: false,
            addEdge: function(edgeData, callback) { 
                callback(edgeData); 
                // Do not clear button visually if we are in Sol-Plot mode!
                if (window.isAddingSoln) {
                    setTimeout(function() { network.disableEditMode(); }, 50);
                } else {
                    window.clearAllButtonStates(); 
                }
            },
            editEdge: false,
            deleteNode: function(data, callback) {
                let nodesToDelete = [...data.nodes]; let edgesToDelete = [...data.edges]; let tsList = [];
                nodesToDelete.forEach(nid => { if (String(nid).startsWith("soln_")) { let ts = String(nid).split("_").pop(); if (!tsList.includes(ts)) tsList.push(ts); }});
                if (tsList.length > 0) {
                    nodes.getIds().forEach(nId => { tsList.forEach(ts => { if (String(nId).startsWith("soln_") && String(nId).endsWith(ts) && !nodesToDelete.includes(nId)) nodesToDelete.push(nId); }); });
                    edges.getIds().forEach(eId => { tsList.forEach(ts => { if ((String(eId).startsWith("edge_x_") || String(eId).startsWith("edge_y_")) && String(eId).endsWith(ts) && !edgesToDelete.includes(eId)) edgesToDelete.push(eId); }); });
                }
                data.nodes = nodesToDelete; data.edges = edgesToDelete; callback(data); 
            },
            deleteEdge: true
        };
        """

        event_listener_injection = """
        window.openStickyEditor = function(nodeId) {
            var clickedNode = nodes.get(nodeId);
            if (!clickedNode) return;
            var domPos = network.canvasToDOM({x: clickedNode.x, y: clickedNode.y});
            var container = network.body.container; var scale = network.getScale();
            network.setOptions({ interaction: { dragView: false, zoomView: false, multiselect: true } }); 
            
            var ta = document.createElement('textarea');
            ta.value = clickedNode.label === "Double-click to edit" ? "" : clickedNode.label; ta.style.position = 'absolute';
            var w = 150 * scale; var h = 150 * scale; ta.style.width = w + 'px'; ta.style.height = h + 'px';
            ta.style.left = (domPos.x - w/2) + 'px'; ta.style.top = (domPos.y - h/2) + 'px'; ta.style.zIndex = 10000;
            ta.style.background = clickedNode.color.background; ta.style.border = '2px dashed rgba(0,0,0,0.5)';
            ta.style.padding = (10 * scale) + 'px'; ta.style.boxSizing = 'border-box'; ta.style.fontFamily = 'arial';
            ta.style.fontSize = (16 * scale) + 'px'; ta.style.color = '#1F2937'; ta.style.resize = 'none'; ta.style.outline = 'none';
            ta.style.textAlign = 'center'; ta.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
            container.appendChild(ta); ta.focus();

            var saveNote = function() {
                if (ta.parentNode) {
                    var newText = ta.value.trim(); clickedNode.label = newText !== "" ? newText : "Double-click to edit";
                    nodes.update(clickedNode); container.removeChild(ta); network.setOptions({ interaction: { dragView: true, zoomView: false, multiselect: true } });
                }
            };
            ta.addEventListener('blur', saveNote); ta.addEventListener('keydown', function(e) { if (e.key === 'Escape') saveNote(); });
        };

        window.updateParameterBox = function() {
            var container = network.body.container; var paramBox = document.getElementById('param-display-box');
            if (!paramBox) { paramBox = document.createElement('div'); paramBox.id = 'param-display-box'; container.appendChild(paramBox); }
            if (!window.isIdeationActive) { paramBox.style.display = 'none'; return; }

            var allNodes = nodes.get(); var allEdges = edges.get(); var extractedParams = [];
            var greenHex = '#10B981'; var redHex = '#EF4444';

            allNodes.forEach(function(n) {
                var borderCol = n.color && n.color.border ? n.color.border : null;
                if (borderCol === greenHex || borderCol === redHex) {
                    allEdges.forEach(function(e) {
                        if (e.from === n.id) {
                            var child = nodes.get(e.to);
                            if (child && child.isPar) {
                                var rawText = child.fullText ? child.fullText : child.label;
                                var cleanText = rawText.replace(/<[^>]*>?/gm, '').replace(/^Parameters:\\s*/i, '');
                                cleanText.split(',').forEach(function(pItem) { var trimmedItem = pItem.trim(); if (trimmedItem) extractedParams.push(trimmedItem); });
                            }
                        }
                    });
                }
            });

            var html = '<div style="font-weight: bold; margin-bottom: 12px; border-bottom: 1px solid #ccc; padding-bottom: 5px;"> Y (unit)</div>';
            if (extractedParams.length === 0) { html += '<div style="font-size: 13px; color: #666; font-style: italic;">No specific parameters found attached to Green or Red shapes.</div>'; } 
            else { html += '<ul>'; extractedParams.forEach(function(p) { html += '<li>' + p + '</li>'; }); html += '</ul>'; }
            paramBox.innerHTML = html; paramBox.style.display = 'block';
        };

        window.clearIdeationBalloons = function(keepActive) {
            if (!keepActive) {
                window.isIdeationActive = false; window.clearAllButtonStates();
                if (window.ideationAnimationId) cancelAnimationFrame(window.ideationAnimationId); window.ideationAnimationId = null;
            }
            if (window.balloonToggleIntervalId) clearInterval(window.balloonToggleIntervalId);
            if (window.tempAddedNodes && window.tempAddedNodes.length > 0) {
                window.tempAddedNodes.forEach(function(nid) { try { nodes.remove(nid); } catch(e){} }); window.tempAddedNodes = [];
            }
            if (window.modifiedOriginalNodes && window.modifiedOriginalNodes.length > 0) {
                window.modifiedOriginalNodes.forEach(function(mod) { 
                    try { 
                        var n = nodes.get(mod.id); 
                        if(n) { if (mod.label !== undefined) n.label = mod.label; if (mod.shapeProperties !== undefined) n.shapeProperties = mod.shapeProperties; if (mod.hidden !== undefined) n.hidden = mod.hidden; nodes.update(n); } 
                    } catch(e){} 
                });
                window.modifiedOriginalNodes = [];
            }
            window.ideationBalloons.forEach(function(b) { if (b.el && b.el.parentNode) b.el.parentNode.removeChild(b.el); }); window.ideationBalloons = [];
        };

        window.spawnBalloons = function(colorBorder) {
            window.clearIdeationBalloons(true); if (colorBorder === null) return; 
            var container = network.body.container; var ideationData = [];
            var greenHex = '#10B981'; var redHex = '#EF4444'; var blackHex = '#000000'; var selectedLabelFirstWord = "OBJECT"; var cNode = null;
            
            var selectedNodesList = network.getSelectedNodes();
            if (selectedNodesList.length > 0) {
                cNode = nodes.get(selectedNodesList[0]);
                if (cNode && cNode.label) { selectedLabelFirstWord = cNode.label.replace(/<[^>]*>?/gm, '').trim().split(/\\s+/)[0].toUpperCase(); }
            }
            
            if (colorBorder === greenHex) {
                ideationData = [
                    { text: "<b>Enhance Function</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(52,211,153,0.9) 60%, rgba(5,150,105,0.9))", tail: "rgba(5,150,105,0.9)" },
                    { text: "<b>Engage Resources</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(52,211,153,0.9) 60%, rgba(5,150,105,0.9))", tail: "rgba(5,150,105,0.9)" },
                    { text: "<b>Copy or Modify or Replace Objects</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(52,211,153,0.9) 60%, rgba(5,150,105,0.9))", tail: "rgba(5,150,105,0.9)" },
                    { text: "<b>Segment, Divide & control objects</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(52,211,153,0.9) 60%, rgba(5,150,105,0.9))", tail: "rgba(5,150,105,0.9)" },
                    { text: "<b>Integrate functions across system</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(52,211,153,0.9) 60%, rgba(5,150,105,0.9))", tail: "rgba(5,150,105,0.9)" }
                ];
            } else if (colorBorder === redHex) {
                ideationData = [
                    { text: "<b>Engage Resources for enhanced Controls </b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(248,113,113,0.9) 60%, rgba(220,38,38,0.9))", tail: "rgba(220,38,38,0.9)" },
                    { text: "<b>Counter Functionality</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(251,146,60,0.9) 60%, rgba(234,88,12,0.9))", tail: "rgba(234,88,12,0.9)" },
                    { text: "<b>Delink</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(248,113,113,0.9) 60%, rgba(220,38,38,0.9))", tail: "rgba(220,38,38,0.9)" },
                    { text: "<b>Eliminate or Replace Objects on the chain</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(244,114,182,0.9) 60%, rgba(219,39,119,0.9))", tail: "rgba(219,39,119,0.9)" },
                    { text: "<b>Copy or Modify Objects on the chain</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(248,113,113,0.9) 60%, rgba(220,38,38,0.9))", tail: "rgba(220,38,38,0.9)" },
                    { text: "<b>Segment, Divide & control object on the chain</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(251,146,60,0.9) 60%, rgba(234,88,12,0.9))", tail: "rgba(234,88,12,0.9)" },
                    { text: "<b>Introduce intermediatory objects</b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(244,114,182,0.9) 60%, rgba(219,39,119,0.9))", tail: "rgba(219,39,119,0.9)" },
                    { text: "<b>Turn Red into Green<b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(167,243,208,0.9) 60%, rgba(16,185,129,0.9))", tail: "rgba(16,185,129,0.9)" }, 
                    { text: "<b>Engage Causes Itself to resolve </b>", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(248,113,113,0.9) 60%, rgba(220,38,38,0.9))", tail: "rgba(220,38,38,0.9)" }
                ];
            } else if (colorBorder === blackHex) {
                var verbs = ["COPY & MODIFY", "ELLIMINATE & TRANSFER FUNCTION FOR", "INTRODUCE LOCAL","ADD NEW","DIVIDE (SEPERATE) & MANAGE","REDEFINE / REPLACE / REALLOCATE"];
                var controls = ["FUNCTION","GEOMETRY-FEATURES","SPECIFIC ENERGY FIELD", "MATERIAL PROPERTY", "INFORMATION"];
                var times = ["IN DESIGN", "IN REAL-TIME", "POST FUNCTION OR TASK"];
                var randomVerb = verbs[Math.floor(Math.random() * verbs.length)]; var randomControl = controls[Math.floor(Math.random() * controls.length)]; var randomTime = times[Math.floor(Math.random() * times.length)];
                var generatedText = randomVerb + " " + selectedLabelFirstWord + " " + randomControl + " " + randomTime + " >>>To Achieve Its Desired State >>> To Control (Y) across XYZ T";
                var boxWidth = container.clientWidth - 40; 
                
                if (cNode) {
                    var nx = cNode.x !== undefined ? cNode.x : 0; var ny = cNode.y !== undefined ? cNode.y : 0; var ts = new Date().getTime();
                    var blackColorObj = { background: '#ffffff', border: '#000000', highlight: { background: '#ffffff', border: '#000000' }, hover: { background: '#ffffff', border: '#000000' } };
                    
                    if (randomVerb === "COPY & MODIFY") { nodes.add({ id: ts, label: cNode.label + "_mod", x: nx + 70, y: ny + 70, shape: cNode.shape || 'dot', size: cNode.size || 30, color: cNode.color || blackColorObj, borderWidth: 3, font: {size: 16, color: '#000000'} }); window.tempAddedNodes.push(ts); } 
                    else if (randomVerb === "ELLIMINATE & TRANSFER FUNCTION FOR") { window.modifiedOriginalNodes.push({id: cNode.id, shapeProperties: {borderDashes: false}}); nodes.update({id: cNode.id, shapeProperties: { borderDashes: [5, 5] }}); } 
                    else if (randomVerb === "INTRODUCE LOCAL") { nodes.add({ id: ts, label: "Local_" + (cNode.label || "Object"), x: nx - 70, y: ny + 70, shape: 'dot', size: 30, color: blackColorObj, borderWidth: 3, font: {size: 16, color: '#000000'} }); window.tempAddedNodes.push(ts); } 
                    else if (randomVerb === "ADD NEW") { nodes.add({ id: ts, label: "New Part or Function", x: nx + 70, y: ny - 70, shape: 'dot', size: 30, color: blackColorObj, borderWidth: 3, font: {size: 16, color: '#000000'} }); window.tempAddedNodes.push(ts); } 
                    else if (randomVerb === "DIVIDE (SEPERATE) & MANAGE") { nodes.add([ { id: ts+1, label: " ", x: nx - 40, y: ny - 40, shape: 'dot', size: 10, color: cNode.color || blackColorObj, borderWidth: 3 }, { id: ts+2, label: " ", x: nx + 40, y: ny - 40, shape: 'dot', size: 10, color: cNode.color || blackColorObj, borderWidth: 3 }, { id: ts+3, label: " ", x: nx, y: ny + 45, shape: 'dot', size: 10, color: cNode.color || blackColorObj, borderWidth: 3 } ]); window.tempAddedNodes.push(ts+1, ts+2, ts+3); } 
                    else if (randomVerb === "REDEFINE / REPLACE / REALLOCATE") { window.modifiedOriginalNodes.push({id: cNode.id, label: cNode.label}); nodes.update({id: cNode.id, label: "Replace_" + cNode.label}); }
                }

                ideationData = [ { text: "<div style='position: absolute; top: -25px; left: 0px; font-size: 1em; color: #495057; font-weight: bold; text-transform: uppercase;'>What if You </div><div style='font-size: 1.1em; font-weight: normal; letter-spacing: 0.5px; width: 100%; text-align: center;'>" + generatedText + "</div>", grad: "linear-gradient(135deg, rgba(31, 41, 55, 0.95), rgba(17, 24, 39, 0.95))", isBox: true, isStatic: true, width: boxWidth, height: 80 } ];
                var triggerList = []; var tailColor = ""; var gradColor = "";

                if (randomControl === "SPECIFIC ENERGY FIELD") {
                   ideationData.push({ text: "<b style='font-size: 0.95em; line-height: 1.3;'>Where else in<br>Nature, World or Other Industry<br>similar Problem is<br>Already Solved?</b>", grad: "radial-gradient(circle at 30% 30%, rgb(255,255,255), rgb(244,114,178) 60%, rgb(219,39,119))", tail: "rgb(219,39,119)", size: 180, fontSize: "13px", isStatic: false });
                   triggerList = ["Resources","Gravity", "Mechanical", "Thermal", "Chemical", "Hydraulic", "Pneumatic", "Vaccum","Flow", "Vibrations", "Rotational", "Electrostatic", "Electrical", "Magnetic", "Optical","Solar","Electromagnetic", "Nuclear", "Bio-intelligence", "Scientific effects"];
                   tailColor = "rgba(245, 158, 11, 0.9)"; gradColor = "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(252,211,77,0.9) 60%, rgba(245,158,11,0.9))";
                } else if (randomControl === "MATERIAL PROPERTY") {
                    triggerList = ["Smart Material","Resources", "Non-linear properties", "Nano-Additives","Composites", "Coating", "Additives", "Phase change", "Mechanical", "Chemical", "Thermal", "Magnetic", "Electrical", "Acoustic", "Optical", "Electromagnetic"];
                    tailColor = "rgba(5, 150, 105, 0.9)"; gradColor = "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(52,211,153,0.9) 60%, rgba(5,150,105,0.9))";
                } else if (randomControl === "GEOMETRY-FEATURES") {
                    triggerList = ["Curviliner Shape", "Mass", "Color","Density","Parts", "Design Controls", "Tolerances", "TROUBLING ELEMENT","Modular Size","Configuration","Features","Resources","Porosity","FLOW","Orthogoanal Dimensions","Thin-Films", "Threads", "Corrugation", "Elasticity"];
                    tailColor = "rgba(37, 99, 235, 0.9)"; gradColor = "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(96,165,250,0.9) 60%, rgba(37,99,235,0.9))";
                } else if (randomControl === "INFORMATION") {
                    triggerList = ["Sensor-Type", "Sensing Parameter", "Sensing_Mechanism","Flow Parameters","Control Parameters","Specifications", "Feedbacks", "IOT","Resources","Digital Twin", "ML", "AI", "Adaptive control", "Real time","DIGITAL", "Dynamic Control"];
                    tailColor = "rgba(147, 51, 234, 0.9)"; gradColor = "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(192,132,252,0.9) 60%, rgba(147,51,234,0.9))";
                } else if (randomControl === "FUNCTION") {
                    triggerList = ["Scientific Phenomenon", "Human Interactions", "Adopt from Other Industry", "Abstract Function", "Reverse roles / Function", "Harmful to Useful","Active Control", "New Energy Source", "New Energy Sink"];
                    tailColor = "rgba(147, 51, 234, 0.9)"; gradColor = "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(192,132,252,0.9) 60%, rgba(147,51,234,0.9))";
                }

                var chunks = 4; var chunkSize = Math.ceil(triggerList.length / chunks);
                for (var i = 0; i < triggerList.length; i += chunkSize) {
                    var chunk = triggerList.slice(i, i + chunkSize);
                    if(chunk.length > 0) ideationData.push({ text: "<b style='font-size: 1.1em; line-height: 1.5;'>" + chunk.join("<br>") + "</b>", grad: gradColor, tail: tailColor, size: 160, fontSize: "12px", isStatic: false });
                }
            } else {
                ideationData = [ { text: "<b>Click a Green, Red, or Black Shape</b><br>to view specific triggers!", grad: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(156,163,175,0.9) 60%, rgba(107,114,128,0.9))", tail: "rgba(107,114,128,0.9)", isStatic: true, size: 200 } ];
            }
            
            ideationData.forEach(function(item) {
                var el = document.createElement('div'); el.innerHTML = item.text; 
                if (item.isBox) { el.className = 'ideation-box'; el.style.width = (item.width || 500) + 'px'; el.style.height = (item.height || 100) + 'px'; el.style.background = item.grad; } 
                else { el.className = 'ideation-balloon'; el.style.setProperty('--bg-gradient', item.grad); el.style.setProperty('--tail-color', item.tail); var sizeToUse = item.size || 140; el.style.width = sizeToUse + 'px'; el.style.height = sizeToUse + 'px'; }
                if (item.fontSize) el.style.fontSize = item.fontSize; container.appendChild(el);
                
                var x, y, vx, vy;
                if (item.isStatic) { if (item.isBox) { x = 20; y = 80; } else { x = (container.clientWidth - (item.size || 140)) / 2; y = (container.clientHeight - (item.size || 140)) / 2; } vx = 0; vy = 0; } 
                else { var elWidth = item.size || 140; var elHeight = item.size || 140; x = Math.random() * (container.clientWidth - elWidth); y = Math.random() * (container.clientHeight - elHeight - 140) + 140; var speedMultiplier = item.size ? 0.6 : 1.2; vx = (Math.random() > 0.5 ? 1 : -1) * (Math.random() * speedMultiplier + 0.4); vy = (Math.random() > 0.5 ? 1 : -1) * (Math.random() * speedMultiplier + 0.4); }
                window.ideationBalloons.push({ el: el, x: x, y: y, vx: vx, vy: vy, isStatic: item.isStatic, isBox: item.isBox });
            });
            
            var balloonsVisible = true;
            window.balloonToggleIntervalId = setInterval(function() {
                balloonsVisible = !balloonsVisible;
                window.ideationBalloons.forEach(function(b) {
                    if (!b.isBox && b.el) {
                        if (balloonsVisible) { b.el.style.visibility = 'visible'; b.el.style.opacity = '1'; } 
                        else { b.el.style.opacity = '0'; setTimeout(function() { if (b.el && b.el.style.opacity === '0') b.el.style.visibility = 'hidden'; }, 3000); }
                    }
                });
            }, 30000); 
        };

        function updateIdeationBalloons() {
            var container = network.body.container; var w = container.clientWidth; var h = container.clientHeight;
            window.ideationBalloons.forEach(function(b) {
                if (b.isStatic) { if (b.isBox) { b.el.style.width = (w - 40) + 'px'; b.x = 20; b.y = 80; } else { b.x = (w - b.el.offsetWidth) / 2; b.y = (h - b.el.offsetHeight) / 2; } } 
                else {
                    b.x += b.vx; b.y += b.vy;
                    if (b.x <= 0) { b.x = 0; b.vx *= -1; } if (b.x + b.el.offsetWidth >= w) { b.x = w - b.el.offsetWidth; b.vx *= -1; }
                    var topCeiling = 170; if (b.y <= topCeiling) { b.y = topCeiling; b.vy *= -1; }
                    if (b.y + b.el.offsetHeight >= h) { b.y = h - b.el.offsetHeight; b.vy *= -1; }
                }
                b.el.style.left = b.x + 'px'; b.el.style.top = b.y + 'px';
            });
            if (window.isIdeationActive) window.ideationAnimationId = requestAnimationFrame(updateIdeationBalloons);
        }

        var customToolbar = document.createElement('div');
        customToolbar.id = 'custom-toolbar';
        network.body.container.appendChild(customToolbar);

        // --- UNIFIED SVG ICONS FOR SELECT BUTTONS ---
        var svgBase = '<svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;">';
        var iconNote = svgBase + '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>';
        var iconPaste = svgBase + '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';
        var iconFit = svgBase + '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>';
        var iconPar = svgBase + '<line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>';
        var iconZoomIn = svgBase + '<line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>';
        var iconZoomOut = svgBase + '<line x1="5" y1="12" x2="19" y2="12"></line></svg>';
        var iconHexagon = svgBase + '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>';

        // --- BUTTON GENERATOR WITH TOOLTIP SUPPORT ---
        function createCustomButton(id, icon, text, onClick, tooltip) {
            var btn = document.createElement('div');
            btn.id = id; btn.className = 'custom-btn'; 
            if (tooltip) btn.title = tooltip; // Add tooltip for icon-only buttons
            
            var htmlStr = '<span style="font-size: 1.2em; display: flex; align-items: center;">' + icon + '</span>';
            if (text && text.trim() !== '') {
                htmlStr += '<span style="margin-left: 5px;">' + text + '</span>';
            }
            btn.innerHTML = htmlStr;
            
            // Protect selection state: stop clicks from reaching document or vis.js container
            btn.addEventListener('mousedown', function(e) { e.stopPropagation(); });
            btn.addEventListener('touchstart', function(e) { e.stopPropagation(); });
            btn.addEventListener('pointerdown', function(e) { e.stopPropagation(); });

            btn.addEventListener('click', function(e) { 
                e.stopPropagation();
                window.clearAllButtonStates(); 
                btn.classList.add('active'); 
                onClick(e); 
            });
            customToolbar.appendChild(btn); return btn;
        }

        // --- CREATING THE MODIFIED BUTTONS ---
        
        var iconNodeStr = '<span style="color: #3B82F6; font-weight: 900; width: 1.2em; height: 1.2em; display: inline-flex; align-items: center; justify-content: center; font-family: Arial, sans-serif;">O</span>';
        var iconEdgeStr = '<span style="width: 1.2em; height: 1.2em; display: inline-flex; align-items: center; justify-content: center;">🔗</span>';
        
        // Node: Bold 'O', No Text, Tooltip
        createCustomButton('c-btn-node', iconNodeStr, '', function() {
            window.isAddingResource = false; window.isAddingNode = true; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false; network.addNodeMode();
        }, 'Node');
        
        // Edge: Original Emoji, No Text, Tooltip
        createCustomButton('c-btn-edge', iconEdgeStr, '', function() {
            window.isAddingResource = false; window.isAddingNode = false; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false; network.addEdgeMode();
        }, 'Edge');
        
        // Resources: Unified SVG Hexagon, No Text, Tooltip
        createCustomButton('c-btn-res', iconHexagon, '', function() {
            window.isAddingResource = true; window.isAddingNode = false; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false; network.addNodeMode();
        }, 'Resources');
        
        // IFR: Original Emoji and Text
        createCustomButton('c-btn-ifr', '&#10024;', 'IFR', function() {
            window.isAddingIFR = true; window.isAddingResource = false; window.isAddingNode = false; window.isAddingPar = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false; network.disableEditMode();
        });
        
        // Parameters: Unified SVG and Text
        createCustomButton('c-btn-par', iconPar, 'Y(x)', function() {
            window.isAddingPar = true; window.isAddingIFR = false; window.isAddingResource = false; window.isAddingNode = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false; network.disableEditMode();
        });
        
        // Idea: Original Emoji, Modified Text
        createCustomButton('c-btn-idea', '💡', 'Idea', function() {
            window.isIdeationActive = !window.isIdeationActive;
            if (window.isIdeationActive) {
                window.isAddingIFR = false; window.isAddingPar = false; window.isAddingResource = false; window.isAddingNode = false; window.isAddingSoln = false; window.isPasting = false; window.isAddingSticky = false; network.disableEditMode();
                var selectedNodes = network.getSelectedNodes(); var nodeColor = null; if (selectedNodes.length > 0) { var cNode = nodes.get(selectedNodes[0]); nodeColor = cNode.color ? cNode.color.border : null; }
                window.spawnBalloons(nodeColor); if (!window.ideationAnimationId) updateIdeationBalloons(); window.updateParameterBox();
            } else {
                window.clearIdeationBalloons(false); document.getElementById('c-btn-idea').classList.remove('active'); window.updateParameterBox();
            }
        });
        
        // Plot: Original Emoji, Modified Text
        createCustomButton('c-btn-soln', '📈', 'Plot', function() {
            window.isAddingSoln = true; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingResource = false; window.isAddingNode = false; window.isIdeationActive = false; window.isPasting = false; window.isAddingSticky = false; network.disableEditMode();
            var existingPlots = nodes.get({ filter: function (item) { return String(item.id).startsWith("soln_o_"); }});
            if (existingPlots.length > 0) { window.showIframeToast("Click on the canvas to drop colored data points."); } else { window.showIframeToast("Left Click to place the X/Y Axes. Subsequent clicks drop data points."); }
        });
        
        // Delete: Original Emoji and Text Modified to "Del"
        createCustomButton('c-btn-del', '🗑️', 'Del', function() {
            network.deleteSelected(); setTimeout(() => document.getElementById('c-btn-del').classList.remove('active'), 200);
        });
        
        // Note: Unified SVG, No Text, Tooltip
        var stickyBtn = createCustomButton('c-btn-sticky', iconNote, '', function() {
            window.isAddingSticky = true; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingResource = false; window.isAddingNode = false; window.isAddingSoln = false; window.isPasting = false; window.isIdeationActive = false; network.disableEditMode();
            window.showIframeToast("Left Click anywhere to drop a sticky note.");
        }, 'Note');
        stickyBtn.style.marginLeft = 'auto'; 
        
        // Paste: Unified SVG, No Text, Tooltip
        var pasteBtn = createCustomButton('c-btn-paste', iconPaste, '', function() {
            window.isAddingResource = false; window.isAddingNode = false; window.isAddingIFR = false; window.isAddingPar = false; window.isAddingSoln = false; window.isIdeationActive = false; window.isAddingSticky = false; window.isPasting = true; network.disableEditMode();
            window.showIframeToast("Ready! Left Click anywhere on the i-board to drop your copied shapes.");
        }, 'Paste');

        // Zoom Out (Continuous Hold)
        var zoomOutBtn = createCustomButton('c-btn-zoom-out', iconZoomOut, '', function() {}, 'Zoom Out');
        var zOutInt = null;
        function stepZoomOut() { 
            var newScale = network.getScale() / 1.03;
            network.moveTo({ scale: newScale, animation: false }); 
            localStorage.setItem('triz_view_scale_TAB_ID', newScale); 
        }
        zoomOutBtn.addEventListener('mousedown', function(e) { e.preventDefault(); stepZoomOut(); zOutInt = setInterval(stepZoomOut, 30); });
        zoomOutBtn.addEventListener('mouseup', function() { clearInterval(zOutInt); setTimeout(() => zoomOutBtn.classList.remove('active'), 150); });
        zoomOutBtn.addEventListener('mouseleave', function() { clearInterval(zOutInt); zoomOutBtn.classList.remove('active'); });
        zoomOutBtn.addEventListener('touchstart', function(e) { e.preventDefault(); stepZoomOut(); zOutInt = setInterval(stepZoomOut, 30); });
        zoomOutBtn.addEventListener('touchend', function() { clearInterval(zOutInt); setTimeout(() => zoomOutBtn.classList.remove('active'), 150); });

        // Zoom In (Continuous Hold)
        var zoomInBtn = createCustomButton('c-btn-zoom-in', iconZoomIn, '', function() {}, 'Zoom In');
        var zInInt = null;
        function stepZoomIn() { 
            var newScale = network.getScale() * 1.03;
            network.moveTo({ scale: newScale, animation: false }); 
            localStorage.setItem('triz_view_scale_TAB_ID', newScale); 
        }
        zoomInBtn.addEventListener('mousedown', function(e) { e.preventDefault(); stepZoomIn(); zInInt = setInterval(stepZoomIn, 30); });
        zoomInBtn.addEventListener('mouseup', function() { clearInterval(zInInt); setTimeout(() => zoomInBtn.classList.remove('active'), 150); });
        zoomInBtn.addEventListener('mouseleave', function() { clearInterval(zInInt); zoomInBtn.classList.remove('active'); });
        zoomInBtn.addEventListener('touchstart', function(e) { e.preventDefault(); stepZoomIn(); zInInt = setInterval(stepZoomIn, 30); });
        zoomInBtn.addEventListener('touchend', function() { clearInterval(zInInt); setTimeout(() => zoomInBtn.classList.remove('active'), 150); });

        // Fit: Unified SVG, No Text, Tooltip
        var fitBtn = createCustomButton('c-btn-fit', iconFit, '', function() {
            network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
            localStorage.removeItem('triz_view_pos_TAB_ID'); 
            localStorage.removeItem('triz_view_scale_TAB_ID');
            setTimeout(() => document.getElementById('c-btn-fit').classList.remove('active'), 200);
        }, 'Fit Canvas');

        window.addEventListener('keydown', function(e) { 
            if (e.key === "Control") network.setOptions({ interaction: { dragView: false, zoomView: false, multiselect: true } }); 
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
                e.preventDefault(); 
                var allNodeIds = nodes.getIds(); 
                var nodesToSelect = allNodeIds; 
                if (nodesToSelect.length > 0) {
                    network.selectNodes(nodesToSelect);
                    var copiedNodes = nodes.get(nodesToSelect); var allEdges = edges.get(); var copiedEdges = allEdges.filter(e => nodesToSelect.includes(e.from) && nodesToSelect.includes(e.to));
                    var nMinX = Math.min(...copiedNodes.map(n => n.x)); var nMaxX = Math.max(...copiedNodes.map(n => n.x)); var nMinY = Math.min(...copiedNodes.map(n => n.y)); var nMaxY = Math.max(...copiedNodes.map(n => n.y));
                    var centerX = (nMinX + nMaxX) / 2; var centerY = (nMinY + nMaxY) / 2;
                    copiedNodes.forEach(n => { n.offsetX = n.x - centerX; n.offsetY = n.y - centerY; });
                    localStorage.setItem('triz_clipboard', JSON.stringify({ nodes: copiedNodes, edges: copiedEdges }));
                    window.showIframeToast("✨ Selected & Copied ALL " + copiedNodes.length + " shapes!<br>Go to another i-board, hit '📋 Paste' and click to drop.");
                } else { window.showIframeToast("i-board is empty. Nothing to copy."); }
            }
        });
        window.addEventListener('keyup', function(e) { if (e.key === "Control") network.setOptions({ interaction: { dragView: true, zoomView: false, multiselect: true } }); });

        var dragBox = false; var rect = { startX: 0, startY: 0, endX: 0, endY: 0 }; var nativeContainer = network.body.container;
        nativeContainer.addEventListener('mousedown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.button === 0) {
                var domRect = nativeContainer.getBoundingClientRect(); 
                var domPos = {x: e.clientX - domRect.left, y: e.clientY - domRect.top};
                if (!network.getNodeAt(domPos)) {
                    dragBox = true; 
                    var pointer = network.DOMtoCanvas(domPos);
                    rect.startX = pointer.x; rect.startY = pointer.y; rect.endX = pointer.x; rect.endY = pointer.y;
                }
            }
        });
        nativeContainer.addEventListener('mousemove', function(e) {
            if (dragBox && (e.ctrlKey || e.metaKey)) {
                var domRect = nativeContainer.getBoundingClientRect(); var pointer = network.DOMtoCanvas({x: e.clientX - domRect.left, y: e.clientY - domRect.top});
                rect.endX = pointer.x; rect.endY = pointer.y; network.redraw(); 
            }
        });
        nativeContainer.addEventListener('mouseup', function(e) { if (dragBox) { dragBox = false; network.redraw(); selectAndCopyNodes(); } });
        network.on("afterDrawing", function(ctx) {
            if (dragBox) { var x = rect.startX; var y = rect.startY; var w = rect.endX - rect.startX; var h = rect.endY - rect.startY; ctx.strokeStyle = "rgba(41, 121, 255, 0.8)"; ctx.fillStyle = "rgba(41, 121, 255, 0.2)"; ctx.lineWidth = 2; ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h); }
        });

        window.showIframeToast = function(msg) {
            var el = document.getElementById('iframe-toast');
            if (!el) { el = document.createElement('div'); el.id = 'iframe-toast'; el.style.cssText = "position:absolute; top:65px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.85); color:#fff; padding:12px 24px; border-radius:50px; z-index:10005; font-family:'Segoe UI', sans-serif; font-size:14px; pointer-events:none; transition: opacity 0.3s; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);"; document.body.appendChild(el); }
            el.innerHTML = msg; el.style.opacity = 1; clearTimeout(window.toastTimer); window.toastTimer = setTimeout(function() { el.style.opacity = 0; }, 3000);
        };

        function selectAndCopyNodes() {
            var minX = Math.min(rect.startX, rect.endX); var maxX = Math.max(rect.startX, rect.endX); var minY = Math.min(rect.startY, rect.endY); var maxY = Math.max(rect.startY, rect.endY);
            var allNodes = nodes.getIds(); var nodePositions = network.getPositions(allNodes); var nodesToSelect = [];
            for (var i = 0; i < allNodes.length; i++) { var nodeId = allNodes[i]; var pos = nodePositions[nodeId]; if (pos.x >= minX && pos.x <= maxX && pos.y >= minY && pos.y <= maxY) { nodesToSelect.push(nodeId); } }
            if (nodesToSelect.length > 0) {
                network.selectNodes(nodesToSelect);
                var copiedNodes = nodes.get(nodesToSelect);
                if (copiedNodes.length === 0) return;
                var allEdges = edges.get(); var copiedEdges = allEdges.filter(e => nodesToSelect.includes(e.from) && nodesToSelect.includes(e.to));
                var nMinX = Math.min(...copiedNodes.map(n => n.x)); var nMaxX = Math.max(...copiedNodes.map(n => n.x)); var nMinY = Math.min(...copiedNodes.map(n => n.y)); var nMaxY = Math.max(...copiedNodes.map(n => n.y));
                var centerX = (nMinX + nMaxX) / 2; var centerY = (nMinY + nMaxY) / 2;
                copiedNodes.forEach(n => { n.offsetX = n.x - centerX; n.offsetY = n.y - centerY; });
                localStorage.setItem('triz_clipboard', JSON.stringify({ nodes: copiedNodes, edges: copiedEdges }));
                window.showIframeToast("✨ Copied " + copiedNodes.length + " shapes!<br>Go to another i-board, hit '📋 Paste' and click to drop.");
            }
        }

        if (triggerClearBoard) {
            var keysToWipe = ['triz_nodes_TAB_ID', 'triz_edges_TAB_ID', 'triz_view_pos_TAB_ID', 'triz_view_scale_TAB_ID', 'triz_selection_TAB_ID'];
            keysToWipe.forEach(function(k) { localStorage.removeItem(k); });
            try { nodes.clear(); } catch(e) {}
            try { edges.clear(); } catch(e) {}
        } else {
            var storedNodes = localStorage.getItem('triz_nodes_TAB_ID'); var storedEdges = localStorage.getItem('triz_edges_TAB_ID');
            if (storedNodes) { try { var parsedNodes = JSON.parse(storedNodes); if (parsedNodes.length > 0) { nodes.clear(); nodes.add(parsedNodes); } } catch(e) {} }
            if (storedEdges) { try { var parsedEdges = JSON.parse(storedEdges); if (parsedEdges.length > 0) { edges.clear(); edges.add(parsedEdges); } } catch(e) {} }
        }

        var zoomAction = """ + js_action_zoom + """;
        var userScale = """ + str(js_view_scale) + """;

        network.once("afterDrawing", function() { 
            if (zoomAction === 'reset') { network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }); localStorage.removeItem('triz_view_pos_TAB_ID'); localStorage.removeItem('triz_view_scale_TAB_ID'); } 
            else if (zoomAction === 'zoom') {
                var savedPos = null; try { savedPos = JSON.parse(localStorage.getItem('triz_view_pos_TAB_ID')); } catch(e) {}
                var moveOpts = { scale: userScale, animation: { duration: 250, easingFunction: 'easeInOutQuad' } }; if (savedPos && savedPos.x !== undefined) moveOpts.position = savedPos;
                network.moveTo(moveOpts); localStorage.setItem('triz_view_scale_TAB_ID', userScale);
            } else {
                var savedPos = null; var savedScale = null;
                try { savedPos = JSON.parse(localStorage.getItem('triz_view_pos_TAB_ID')); } catch(e) {}
                try { savedScale = parseFloat(localStorage.getItem('triz_view_scale_TAB_ID')); } catch(e) {}
                if (savedPos && savedPos.x !== undefined && savedScale && !isNaN(savedScale)) { network.moveTo({ position: savedPos, scale: savedScale }); } else { network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } }); }
            }
            
            var savedSelection = []; try { savedSelection = JSON.parse(localStorage.getItem('triz_selection_TAB_ID') || "[]"); } catch(e) {}
            if (savedSelection.length > 0) {
                var validSelection = savedSelection.filter(function(id) { return nodes.get(id) !== null; });
                if (validSelection.length > 0) { try { network.selectNodes(validSelection); } catch(e) {} }
            }
        });
        
        network.on("dragEnd", function(params) { localStorage.setItem('triz_view_pos_TAB_ID', JSON.stringify(network.getViewPosition())); });

        var colorChangedTrigger = """ + js_color_changed + """;
        var savedSelection = []; try { savedSelection = JSON.parse(localStorage.getItem('triz_selection_TAB_ID') || "[]"); } catch(e) {}
        if (colorChangedTrigger && savedSelection.length > 0) {
            for (var i = 0; i < savedSelection.length; i++) {
                var nId = savedSelection[i]; var node = nodes.get(nId);
                if (node && !String(node.id).startsWith("sticky_")) { node.color = { background: defaultBg, border: defaultBorder, highlight: { background: defaultBg, border: defaultBorder }, hover: { background: defaultBg, border: defaultBorder } }; nodes.update(node); }
            }
            localStorage.setItem('triz_nodes_TAB_ID', JSON.stringify(nodes.get()));
        }

        nodes.on('*', function () { localStorage.setItem('triz_nodes_TAB_ID', JSON.stringify(nodes.get())); }); edges.on('*', function () { localStorage.setItem('triz_edges_TAB_ID', JSON.stringify(edges.get())); });

        network.on("selectNode", function(params) {
            var selected = params.nodes; var newSelection = [...selected]; var changed = false;
            selected.forEach(function(nid) {
                if(String(nid).startsWith("soln_")) {
                    var ts = String(nid).split("_").pop(); var allIds = nodes.getIds();
                    allIds.forEach(function(id) { if(String(id).startsWith("soln_") && String(id).endsWith(ts) && !newSelection.includes(id)) { newSelection.push(id); changed = true; } });
                }
            });
            if (changed) { network.selectNodes(newSelection); localStorage.setItem('triz_selection_TAB_ID', JSON.stringify(newSelection)); } 
            else { localStorage.setItem('triz_selection_TAB_ID', JSON.stringify(params.nodes)); }
        });
        network.on("deselectNode", function(params) { localStorage.setItem('triz_selection_TAB_ID', JSON.stringify(params.nodes)); });

        function enforcePlotRigidity(draggedNodes, pos, updates) {
            var refNodeId = draggedNodes.find(id => String(id).startsWith("soln_"));
            if (refNodeId) {
                var ts = String(refNodeId).split("_").pop(); var type = String(refNodeId).split("_")[1]; 
                if (type !== 'pt') {
                    var nx = pos[refNodeId].x; var ny = pos[refNodeId].y; var ox, oy;
                    if (type === 'o') { ox = nx; oy = ny; } else if (type === 'xa') { ox = nx - 500; oy = ny; } else if (type === 'ya') { ox = nx; oy = ny + 500; } else if (type === 'x') { ox = nx - 500; oy = ny + 20; } else if (type === 'y') { ox = nx - 40; oy = ny + 500; }
                    if (nodes.get("soln_o_" + ts)) updates.push({ id: "soln_o_" + ts, x: ox, y: oy });
                    if (nodes.get("soln_xa_" + ts)) updates.push({ id: "soln_xa_" + ts, x: ox + 500, y: oy });
                    if (nodes.get("soln_ya_" + ts)) updates.push({ id: "soln_ya_" + ts, x: ox, y: oy - 500 });
                    if (nodes.get("soln_x_" + ts)) updates.push({ id: "soln_x_" + ts, x: ox + 500, y: oy - 20 });
                    if (nodes.get("soln_y_" + ts)) updates.push({ id: "soln_y_" + ts, x: ox + 40, y: oy - 500 });
                }
            }
        }

        network.on("dragEnd", function(params) {
            if (params.nodes.length > 0) {
                var pos = network.getPositions(params.nodes); var updates = [];
                for (var i = 0; i < params.nodes.length; i++) {
                    var nodeId = params.nodes[i]; var node = nodes.get(nodeId);
                    if (node && !node.fixed && !String(nodeId).startsWith("soln_")) { node.x = pos[nodeId].x; node.y = pos[nodeId].y; updates.push(node); }
                }
                enforcePlotRigidity(params.nodes, pos, updates); if(updates.length > 0) nodes.update(updates);
            }
        });

        network.on("dragging", function(params) {
            if (params.nodes.length > 0) {
                var pos = network.getPositions(params.nodes); var updates = [];
                for (var i = 0; i < params.nodes.length; i++) { var nodeId = params.nodes[i]; if (!String(nodeId).startsWith("soln_")) updates.push({ id: nodeId, x: pos[nodeId].x, y: pos[nodeId].y }); }
                enforcePlotRigidity(params.nodes, pos, updates); if(updates.length > 0) nodes.update(updates);
            }
        });

        network.body.container.oncontextmenu = function() { return false; };

        // --- DESELECTION LOGIC ---
        window.clearSelectionState = function() {
            if (typeof network !== 'undefined') {
                network.unselectAll();
                localStorage.setItem('triz_selection_TAB_ID', JSON.stringify([]));
            }
        };

        document.addEventListener('mousedown', function(e) {
            if (!e.target.closest('canvas') && !e.target.closest('.custom-btn')) {
                window.clearSelectionState();
            }
            if (!e.target.closest('canvas') && !e.target.closest('#custom-toolbar') && !e.target.closest('#param-display-box')) {
                if (window.isIdeationActive) { window.spawnBalloons(null); window.updateParameterBox(); }
            }
        });

        window.addEventListener('blur', function() {
            window.clearSelectionState();
            if (window.isIdeationActive) window.spawnBalloons(null);
        });

        network.on("click", function (params) {
            
            if (params.event.srcEvent && params.event.srcEvent.target && params.event.srcEvent.target.closest('#custom-toolbar')) {
                if (!params.event.srcEvent.target.closest('.custom-btn')) {
                    window.clearSelectionState();
                }
                return;
            }
            
            // 1. HIGHEST PRIORITY: Shift + Click (Color Change)
            if (params.event.srcEvent.shiftKey && params.nodes.length > 0) {
                var nodeId = params.nodes[0]; var clickedNode = nodes.get(nodeId);
                
                if (String(nodeId).startsWith("sticky_")) {
                    var stickyColors = ['#FEF08A', '#FBCFE8', '#BAE6FD', '#BBF7D0', '#FFEDD5', '#E9D5FF'];
                    var randColor = stickyColors[Math.floor(Math.random() * stickyColors.length)];
                    clickedNode.color = { background: randColor, border: randColor, highlight: { background: randColor, border: randColor }, hover: { background: randColor, border: randColor } };
                    nodes.update(clickedNode);
                } else if (String(nodeId).startsWith("plotpt_")) {
                    var ptColors = ['#FCA5A5', '#FCD34D', '#FDE047', '#86EFAC', '#93C5FD', '#C4B5FD', '#F9A8D4', '#FDA4AF', '#6EE7B7', '#34D399', '#60A5FA', '#A78BFA', '#F472B6', '#FB7185', '#E879F9', '#38BDF8', '#4ADE80', '#A3E635'];
                    var rCol = ptColors[Math.floor(Math.random() * ptColors.length)];
                    clickedNode.color = { background: rCol, border: rCol, highlight: { background: rCol, border: rCol }, hover: { background: rCol, border: rCol } };
                    clickedNode.borderWidth = 0;
                    clickedNode.font = {color: '#000000'};
                    nodes.update(clickedNode);
                } else {
                    var palette = ['#000000', '#10B981', '#EF4444', '#3B82F6', '#A855F7'];
                    var currentBorder = (clickedNode.color && clickedNode.color.border) ? clickedNode.color.border : defaultBorder;
                    var currentIndex = palette.indexOf(currentBorder); if (currentIndex === -1) currentIndex = 0; 
                    var nextColor = palette[(currentIndex + 1) % palette.length];
                    clickedNode.color = { background: '#ffffff', border: nextColor, highlight: { background: '#ffffff', border: nextColor }, hover: { background: '#ffffff', border: nextColor } };
                    nodes.update(clickedNode);
                    if (window.isIdeationActive) window.spawnBalloons(nextColor);
                }
                return; 
            }
            
            // 2. PASTE DROP LOGIC
            if (window.isPasting) {
                if (params.pointer && params.pointer.canvas) {
                    var cx = params.pointer.canvas.x; var cy = params.pointer.canvas.y; var clipStr = localStorage.getItem('triz_clipboard');
                    if (clipStr) {
                        try {
                            var clip = JSON.parse(clipStr);
                            if (clip.nodes && clip.nodes.length > 0) {
                                var tsOff = new Date().getTime(); var newNodes = []; var idMap = {};
                                clip.nodes.forEach(function(n, idx) { 
                                    var newId = tsOff + idx; 
                                    var strId = String(n.id);
                                    if (strId.startsWith("soln_")) {
                                        var parts = strId.split("_");
                                        newId = parts[0] + "_" + parts[1] + "_" + tsOff; 
                                    } else if (strId.startsWith("sticky_")) {
                                        newId = "sticky_" + newId;
                                    } else if (strId.startsWith("plotpt_")) {
                                        newId = "plotpt_" + newId;
                                    }
                                    idMap[n.id] = newId; 
                                    var cloned = Object.assign({}, n, { id: newId, x: cx + n.offsetX, y: cy + n.offsetY }); 
                                    delete cloned.offsetX; delete cloned.offsetY; 
                                    newNodes.push(cloned); 
                                });
                                var newEdges = [];
                                if (clip.edges) { clip.edges.forEach(function(e, idx) { if (idMap[e.from] && idMap[e.to]) { var cloned = Object.assign({}, e, { id: "edge_" + tsOff + "_" + idx, from: idMap[e.from], to: idMap[e.to] }); newEdges.push(cloned); } }); }
                                nodes.add(newNodes); edges.add(newEdges); window.showIframeToast("✅ Successfully pasted " + newNodes.length + " shapes!"); network.selectNodes(Object.values(idMap)); 
                            } else { window.showIframeToast("Clipboard is empty."); }
                        } catch(e) { console.error(e); }
                    } else { window.showIframeToast("Clipboard is empty."); }
                }
                window.isPasting = false; window.clearAllButtonStates(); return;
            }

            // 3. SOL-PLOT & DATA POINT CREATION
            if (window.isAddingSoln) {
                if (params.nodes.length === 0 && params.edges.length === 0) {
                    if (params.pointer && params.pointer.canvas) {
                        var cx = params.pointer.canvas.x; var cy = params.pointer.canvas.y; var ts = new Date().getTime();
                        var existingPlots = nodes.get({ filter: function (item) { return String(item.id).startsWith("soln_o_"); }});
                        
                        if (existingPlots.length === 0) {
                            nodes.add([
                                { id: "soln_o_" + ts, x: cx, y: cy, label: " ", shape: 'square', size: 6, color: '#000000', physics: false, fixed: false },
                                { id: "soln_xa_" + ts, x: cx + 500, y: cy, label: " ", shape: 'text', physics: false, fixed: false },
                                { id: "soln_ya_" + ts, x: cx, y: cy - 500, label: " ", shape: 'text', physics: false, fixed: false },
                                { id: "soln_x_" + ts, x: cx + 500, y: cy - 20, label: "X Axis", shape: 'text', physics: false, fixed: false, font: {size: 16, color: '#000000', bold: true} },
                                { id: "soln_y_" + ts, x: cx + 40, y: cy - 500, label: "Y Axis", shape: 'text', physics: false, fixed: false, font: {size: 16, color: '#000000', bold: true} }
                            ]);
                            edges.add([
                                { id: "edge_x_" + ts, from: "soln_o_" + ts, to: "soln_xa_" + ts, arrows: { to: { enabled: true, type: 'arrow', scaleFactor: 0.8 } }, color: {color: '#8B4513'}, width: 2, physics: false, smooth: false },
                                { id: "edge_y_" + ts, from: "soln_o_" + ts, to: "soln_ya_" + ts, arrows: { to: { enabled: true, type: 'arrow', scaleFactor: 0.8 } }, color: {color: '#8B4513'}, width: 2, physics: false, smooth: false }
                            ]);
                        } else {
                            var ptColors = ['#FCA5A5', '#FCD34D', '#FDE047', '#86EFAC', '#93C5FD', '#C4B5FD', '#F9A8D4', '#FDA4AF', '#6EE7B7', '#34D399', '#60A5FA', '#A78BFA', '#F472B6', '#FB7185', '#E879F9', '#38BDF8', '#4ADE80', '#A3E635'];
                            var rCol = ptColors[Math.floor(Math.random() * ptColors.length)];
                            nodes.add({ id: "plotpt_" + ts, x: cx, y: cy, label: " ", shape: 'dot', size: 12, color: { background: rCol, border: rCol, highlight: { background: rCol, border: rCol }, hover: { background: rCol, border: rCol } }, borderWidth: 0, font: {color: '#000000'}, physics: false, fixed: false });
                        }
                    }
                }
                return;
            }

            // 4. STICKY NOTE CREATION LOGIC
            if (window.isAddingSticky) {
                if (params.nodes.length === 0 && params.edges.length === 0) {
                    if (params.pointer && params.pointer.canvas) {
                        var cx = params.pointer.canvas.x; var cy = params.pointer.canvas.y;
                        var colors = [ {bg: '#FEF08A'}, {bg: '#FBCFE8'}, {bg: '#BAE6FD'}, {bg: '#BBF7D0'}, {bg: '#FFEDD5'}, {bg: '#E9D5FF'} ];
                        var randColor = colors[Math.floor(Math.random() * colors.length)]; var ts = new Date().getTime(); var stickyId = "sticky_" + ts;

                        nodes.add({
                            id: stickyId, label: "Double-click to edit", x: cx, y: cy, shape: 'box', margin: 10, borderWidth: 0, 
                            widthConstraint: { minimum: 150, maximum: 150 }, heightConstraint: { minimum: 150, valignment: 'middle' }, shapeProperties: { borderRadius: 0 }, 
                            color: { background: randColor.bg, border: randColor.bg, highlight: { background: randColor.bg, border: randColor.bg }, hover: { background: randColor.bg, border: randColor.bg } },
                            font: { size: 16, color: '#1F2937', face: 'arial', bold: false, multi: true, align: 'center' }, shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 5, x: 3, y: 3 }
                        });
                        
                        window.isAddingSticky = false; window.clearAllButtonStates(); setTimeout(function() { window.openStickyEditor(stickyId); }, 50); 
                    }
                }
                return;
            }

            if (window.isIdeationActive) {
                if (params.nodes.length > 0) {
                    var clickedNode = nodes.get(params.nodes[0]); var nodeColor = (clickedNode.color && clickedNode.color.border) ? clickedNode.color.border : defaultBorder;
                    window.spawnBalloons(nodeColor); 
                } else { window.spawnBalloons(null); }
            }
            
            if (!window.isAddingIFR && !window.isAddingPar && !window.isAddingNode && !window.isAddingResource && !window.isAddingSoln && !window.isAddingSticky && !params.event.srcEvent.shiftKey && !params.event.srcEvent.ctrlKey && !params.event.srcEvent.metaKey && params.nodes.length === 1) {
                var clickedId = params.nodes[0]; var cNode = nodes.get(clickedId);
                if (cNode && (cNode.isIFR || cNode.isPar)) {
                    var bgColor = cNode.isIFR ? '#8B4513' : '#0F766E'; 
                    if (cNode.expanded) {
                        cNode.expanded = false; cNode.shape = 'dot'; cNode.size = 12; cNode.label = '+'; cNode.borderWidth = 2; cNode.shadow = false; cNode.margin = 5; 
                        cNode.color = { background: bgColor, border: defaultBorder }; cNode.font = Object.assign({}, cNode.font || {}, { multi: false }); 
                        var targetEdge = edges.get(cNode.id + "_edge"); if (targetEdge) { targetEdge.smooth = { type: 'continuous' }; edges.update(targetEdge); }
                    } else {
                        cNode.expanded = true; cNode.shape = 'box'; cNode.label = "<i>" + cNode.fullText + "</i>"; cNode.borderWidth = 0; cNode.margin = { top: 25, right: 35, bottom: 25, left: 35 }; cNode.font = Object.assign({}, cNode.font || {}, { multi: 'html' }); 
                        cNode.color = { background: bgColor, border: '#FFFFFF' }; cNode.shadow = { enabled: true, color: 'rgba(0,0,0,0.2)', size: 6, x: 3, y: 3 };
                        var targetEdge = edges.get(cNode.id + "_edge"); if (targetEdge) { targetEdge.smooth = { type: 'continuous' }; edges.update(targetEdge); }
                    }
                    nodes.update(cNode); return; 
                }
            }

            if (window.isAddingIFR) {
                if (params.nodes.length > 0) {
                    var targetNodeId = params.nodes[0]; var targetNode = nodes.get(targetNodeId);
                    var baseLabel = targetNode.label || "Object"; baseLabel = baseLabel.replace(/<[^>]*>?/gm, '').trim(); 
                    var finalLabel = ""; var firstSpaceIndex = baseLabel.indexOf(" ");
                    if (firstSpaceIndex !== -1) { var subject = baseLabel.substring(0, firstSpaceIndex); var state = baseLabel.substring(firstSpaceIndex + 1).toLowerCase(); finalLabel = "IFR: " + subject + " achieves the desired state of being " + state + " all by ITSELF"; } 
                    else { finalLabel = "IFR: " + baseLabel + " achieves desired state all by ITSELF"; }
                    var newNodeId = new Date().getTime();
                    nodes.add({ id: newNodeId, label: "<i>" + finalLabel + "</i>", fullText: finalLabel, isIFR: true, expanded: true, x: targetNode.x + 80, y: targetNode.y - 80, shape: 'box', margin: { top: 25, right: 35, bottom: 25, left: 35 }, borderWidth: 0, shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 6, x: 3, y: 3 }, font: { size: 14, face: 'arial', color: '#FFFFFF', multi: 'html' }, color: { background: '#8B4513', border: '#FFFFFF' } });
                    edges.add({ id: newNodeId + "_edge", from: targetNodeId, to: newNodeId, dashes: true, arrows: { to: { enabled: false }, from: { enabled: false } }, color: { color: '#666666' } });
                }
                window.isAddingIFR = false; window.clearAllButtonStates(); return; 
            }

            if (window.isAddingPar) {
                if (params.nodes.length > 0) {
                    var targetNodeId = params.nodes[0]; var targetNode = nodes.get(targetNodeId);
                    var userLabel = prompt("Enter Parameters:", "a, b, c");
                    if (userLabel !== null && userLabel.trim() !== "") {
                        var finalLabel = "Parameters: " + userLabel.replace(/^Parameters:\s*/i, ''); var newNodeId = new Date().getTime();
                        nodes.add({ id: newNodeId, label: "<i>" + finalLabel + "</i>", fullText: finalLabel, isPar: true, expanded: true, x: targetNode.x - 80, y: targetNode.y - 80, shape: 'box', margin: { top: 25, right: 35, bottom: 25, left: 35 }, borderWidth: 0, shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 6, x: 3, y: 3 }, font: { size: 14, face: 'arial', color: '#FFFFFF', multi: 'html' }, color: { background: '#0F766E', border: '#FFFFFF' } });
                        edges.add({ id: newNodeId + "_edge", from: targetNodeId, to: newNodeId, dashes: true, arrows: { to: { enabled: false }, from: { enabled: false } }, color: { color: '#666666' } });
                    }
                }
                window.isAddingPar = false; window.clearAllButtonStates(); return; 
            }

            if (autoCreateEnabled && params.nodes.length === 0 && params.edges.length === 0 && !params.event.srcEvent.ctrlKey && !params.event.srcEvent.metaKey) {
                if (window.isAddingResource || window.isAddingNode || window.isAddingIFR || window.isAddingPar || window.isAddingSoln || window.isAddingSticky) return; 
                var label = prompt("Enter Object and its State:", "Object : State");
                if (label !== null && label.trim() !== "") {
                    var pointer = params.pointer.canvas;
                    nodes.add({ id: new Date().getTime(), label: label, x: pointer.x, y: pointer.y, shape: 'dot', size: 30, borderWidth: 3, color: { background: defaultBg, border: defaultBorder, highlight: { background: defaultBg, border: defaultBorder }, hover: { background: defaultBg, border: defaultBorder } }, font: { size: 16, face: 'arial', vadjust: 5, color: defaultBorder } });
                }
            }
        });

        network.on("oncontext", function (params) {
            params.event.preventDefault();
            if (params.event && params.event.target && params.event.target.closest('#custom-toolbar')) return;
            
            // --- UNIVERSAL RIGHT-CLICK CONNECTION LOGIC ---
            if (window.isAddingSoln) {
                network.addEdgeMode();
                return;
            }
            
            window.isAddingSticky = false; 
            window.isAddingSoln = false; 
            window.isPasting = false;
            window.isAddingResource = false;
            window.isAddingNode = false;
            window.isAddingIFR = false;
            window.isAddingPar = false;
            window.clearAllButtonStates();
            
            network.addEdgeMode();
            var edgeBtn = document.getElementById('c-btn-edge');
            if (edgeBtn) edgeBtn.classList.add('active');
        });

        network.on("doubleClick", function (params) {
            
            if (params.event.srcEvent && params.event.srcEvent.target && params.event.srcEvent.target.closest('#custom-toolbar')) return;
            
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0]; 
                var clickedNode = nodes.get(nodeId);
                var isSticky = String(clickedNode.id).startsWith("sticky_");

                if (isSticky) {
                    window.openStickyEditor(nodeId);
                    return; 
                }

                var isRes = clickedNode.shape === 'hexagon'; 
                var isIFR = clickedNode.isIFR; 
                var isPar = clickedNode.isPar; 
                var isSolnLabel = String(clickedNode.id).startsWith("soln_x_") || String(clickedNode.id).startsWith("soln_y_");
                var isPlotPt = String(clickedNode.id).startsWith("plotpt_");
                
                var promptText = "Edit Object and its State:";
                if (isRes) promptText = "Edit Resource Name:"; 
                else if (isIFR) promptText = "Edit IFR Concept:"; 
                else if (isPar) promptText = "Edit Parameters:"; 
                else if (isSolnLabel) promptText = "Edit Axis Label:";
                else if (isPlotPt) promptText = "Edit Data Point Label:";
                
                var currentText = (isIFR || isPar) ? (clickedNode.fullText || clickedNode.label) : clickedNode.label;
                if (isIFR) currentText = currentText.replace(/^IFR:\\s*/i, ''); 
                if (isPar) currentText = currentText.replace(/^Parameters:\\s*/i, '');
                
                var newLabel = prompt(promptText, currentText);
                if (newLabel !== null && newLabel.trim() !== "") {
                    if (isIFR) { newLabel = "IFR: " + newLabel; clickedNode.fullText = newLabel; if (clickedNode.expanded) clickedNode.label = "<i>" + newLabel + "</i>"; } 
                    else if (isPar) { newLabel = "Parameters: " + newLabel; clickedNode.fullText = newLabel; if (clickedNode.expanded) clickedNode.label = "<i>" + newLabel + "</i>"; } 
                    else { clickedNode.label = newLabel; }
                    nodes.update(clickedNode);
                }
            }
        });
        """
        
        # Format the local storage keys dynamically to prevent bleeding between tabs
        event_listener_injection = event_listener_injection.replace("TAB_ID", str(tab_id))
        
        source_code = source_code.replace("</head>", custom_css + "\n</head>")
        
        source_code = source_code.replace(
            "network = new vis.Network(container, data, options);", 
            js_injection + "\nnetwork = new vis.Network(container, data, options);\n" + "// --- FONT-COLOR SYNC SHIM ---\n(function(){\n  function getBorder(c){ if(!c) return defaultBorder; if(typeof c==='string') return defaultBorder; return c.border?c.border:defaultBorder;}\n  var _a = nodes.add.bind(nodes); nodes.add = function(it){ function sync(n){ if(!n) return n; var b=getBorder(n.color); if(!String(n.id).startsWith('sticky_') && !String(n.id).startsWith('plotpt_')){ n.font = Object.assign({}, n.font||{}, {color:b}); } else if(String(n.id).startsWith('plotpt_')) { n.font = Object.assign({}, n.font||{}, {color:'#000000'}); } return n;} if(Array.isArray(it)) return _a(it.map(sync)); return _a(sync(it)); };\n  var _u = nodes.update.bind(nodes); nodes.update = function(it){ function sync(n){ if(!n) return n; var b=getBorder(n.color); if(!n.color){ try{ var ex=nodes.get(n.id); if(ex&&ex.color) b=getBorder(ex.color);}catch(e){} } if(!String(n.id).startsWith('sticky_') && !String(n.id).startsWith('plotpt_')){ n.font = Object.assign({}, n.font||{}, {color:b}); } else if(String(n.id).startsWith('plotpt_')) { n.font = Object.assign({}, n.font||{}, {color:'#000000'}); } return n;} if(Array.isArray(it)) return _u(it.map(sync)); return _u(sync(it)); };\n  try{ var all = nodes.get(); for(var i=0;i<all.length;i++){ var n=all[i]; var b=getBorder(n.color); if(!String(n.id).startsWith('sticky_') && !String(n.id).startsWith('plotpt_')){ n.font = Object.assign({}, n.font||{}, {color:b}); } else if(String(n.id).startsWith('plotpt_')) { n.font = Object.assign({}, n.font||{}, {color:'#000000'}); } } nodes.update(all);}catch(e){}\n})();\n" + event_listener_injection
        )
        
        source_code += f"\n\n"

        os.remove(tmp_file.name)
        
        # Render the PyVis frame
        components.html(source_code, height=720, scrolling=False)

    except Exception as e:
        st.error(f"Error rendering diagram: {e}")

# -------------------- MAIN TABS UI --------------------
st.markdown(
    '<hr style="border: none; height: 3px; background-color: red; margin-top: -10px; margin-bottom: 2px;">'
    '<div style="text-align: right; font-style: italic; color: #f5f5f5; font-size: 14px; margin-top: 0px; margin-bottom: 15px;">Brought to you by Knowledge-Station</div>', 
    unsafe_allow_html=True
)

# Create a sleek, aligned row for the Title and the Add Canvas button just above the tabs
col_title_input, col_add_btn = st.columns([0.85, 0.15])
with col_title_input:
    st.text_area("Project Title", value="Description :", label_visibility="collapsed", height=68)
    
with col_add_btn:
    if st.button("➕ i-board", type="primary", use_container_width=True):
        if len(st.session_state.canvas_ids) < 9:
            st.session_state.canvas_ids.append(st.session_state.next_canvas_id)
            st.session_state.next_canvas_id += 1
            st.rerun()
        else:
            st.toast("Maximum limit of 9 i-boards reached!", icon="⚠️")

tab_titles = [f"i-board {i+1}" for i in range(len(st.session_state.canvas_ids))]
tabs = st.tabs(tab_titles)

# Render existing canvases
for idx, internal_id in enumerate(st.session_state.canvas_ids):
    display_num = idx + 1
    with tabs[idx]:
        render_canvas(tab_id=str(internal_id), display_num=display_num)

# -------------------- BOTTOM UI FOR RECORDING IDEAS --------------------
st.markdown("### 💡 Record Your Idea")

with st.form("idea_form", clear_on_submit=True):
    new_idea = st.text_area("Type your idea here:", height=100, label_visibility="collapsed", placeholder="e.g., Modify the geometry to allow segmented cooling...")
    col1, col2 = st.columns([0.15, 0.85])
    with col1:
        submitted = st.form_submit_button("Save Idea", type="primary", use_container_width=True)
        
    if submitted:
        if new_idea.strip():
            st.session_state.ideas.append({
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "Idea": new_idea.strip()
            })
            st.success("Idea saved successfully! You can download your ideas from the sidebar.")
        else:
            st.warning("Please enter some text before saving.")
            
if st.session_state.ideas:
    with st.expander(f"View Saved Ideas ({len(st.session_state.ideas)})", expanded=False):
        for idx, idea in enumerate(st.session_state.ideas):
            st.markdown(f"**{idx+1}.** {idea['Idea']}  \n*(Saved: {idea['Timestamp']})*")
            st.markdown("---")
