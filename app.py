# INSERT_YOUR_REWRITE_HERE
import streamlit as st
import os
import tempfile
from shopping_agent import shopping_agent
from langchain_core.messages import AIMessage, HumanMessage

st.title("Shopping Agent Assistant 🛒")

# Initialize the chat/session history in Streamlit session_state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "ai", "content": "Hello! I'm your shopping assistant. How can I help you today?"}
    ]

# Option to upload an image
st.markdown("**Or upload a product image:**")
uploaded_file = st.file_uploader("Upload an image (.jpg, .jpeg, .png)", type=["jpg", "jpeg", "png"])

# Conditionally enable the "Go ahead" button after an image is uploaded
img_btn_disabled = uploaded_file is None

if uploaded_file is not None:
    st.success("Image uploaded! Click 'Go ahead' to search for this product.")

go_ahead = st.button("Go ahead", disabled=img_btn_disabled)

# Show the conversation history
for msg in st.session_state["messages"]:
    if msg["role"] == "human":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.write(msg["content"])

# Streamlit chat input (disabled if processing an image for clarity)
user_input = st.chat_input("What would you like to buy?") if not (go_ahead and uploaded_file is not None) else None

if go_ahead and uploaded_file is not None:
    # Save the uploaded image to a temporary file for processing
    suffix = "." + uploaded_file.name.split(".")[-1] if "." in uploaded_file.name else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = tmp_file.name

    # Add special message to the history for clarity and traceability
    msg_text = f"""
    I have uploaded a product image.
    The image is located at:
    {tmp_path}
    Please analyze this image using the identify_object_in_image tool and help me find matching products.
    """
    st.session_state["messages"].append({"role": "human", "content": msg_text})

    # Convert chat history to LangChain format
    lc_history = []
    for msg in st.session_state["messages"]:
        if msg["role"] == "human":
            lc_history.append(HumanMessage(content=msg["content"]))
        else:
            lc_history.append(AIMessage(content=msg["content"]))

    # Call the agent with the image path
    try:
        result = shopping_agent.invoke({"messages": lc_history, "image_path": tmp_path})
        if isinstance(result, dict) and "messages" in result and hasattr(result["messages"][-1], "content"):
            bot_reply = result["messages"][-1].content
        else:
            bot_reply = str(result)
    except Exception as e:
        bot_reply = f"Sorry, there was an error processing the image: {str(e)}"

    # Store bot response
    st.session_state["messages"].append({"role": "ai", "content": bot_reply})

    # Show last agent reply
    with st.chat_message("assistant"):
        st.write(bot_reply)

    # Remove the temp file safely
    try:
        os.remove(tmp_path)
    except Exception:
        pass

elif user_input:
    # Store user's message
    st.session_state["messages"].append({"role": "human", "content": user_input})

    # Convert chat history to LangChain messages
    lc_history = []
    for msg in st.session_state["messages"]:
        if msg["role"] == "human":
            lc_history.append(HumanMessage(content=msg["content"]))
        else:
            lc_history.append(AIMessage(content=msg["content"]))

    # Send to agent
    try:
        result = shopping_agent.invoke({"messages": lc_history})
        if isinstance(result, dict) and "messages" in result and hasattr(result["messages"][-1], "content"):
            bot_reply = result["messages"][-1].content
        else:
            bot_reply = str(result)
    except Exception as e:
        bot_reply = f"Sorry, there was an error: {str(e)}"

    # Store bot response
    st.session_state["messages"].append({"role": "ai", "content": bot_reply})

    # Show last agent reply
    with st.chat_message("assistant"):
        st.write(bot_reply)