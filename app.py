# INSERT_YOUR_REWRITE_HERE
import streamlit as st
import os
import tempfile

# Define lazy loading/caching for heavy imports to optimize reload speed

@st.cache_resource
def get_shopping_agent():
    from shopping_agent import shopping_agent
    return shopping_agent

# Main screen title
st.title("Shopping Agent Assistant 🛒")
st.markdown("🔗 **[Learn how this project works](https://vakul-singh.vercel.app/projects/shopping-agent)**")
st.markdown("💬 **Try typing natural prompts like:** *\"search honey less than $20 which is organic and has more than 4 rating\"*")

# Sidebar for project links and categories
with st.sidebar:
    st.header("Controls & Info 🛠️")
    st.markdown("🔗 **[Learn how this project works](https://vakul-singh.vercel.app/projects/shopping-agent)**")
    st.markdown("🌐 **[My Portfolio](https://vakul-singh.vercel.app/)**")
    st.markdown("📄 **[My Resume](https://drive.google.com/drive/folders/1VfNSI8ek9rNOHqHo2R5Epx_67XMHbESk?usp=drive_link)**")
    
    # Available product categories expander
    with st.sidebar.expander("📦 Available Product Categories", expanded=True):
        st.markdown("Feel free to search for products in the following categories:")
        categories = [
            "🍯 Honey",
            "🫒 Oils",
            "🥜 Nuts & Trail Mix",
            "🌾 Grains & Rice",
            "☕ Tea & Coffee",
            "🥣 Granola",
            "🥛 Plant-Based Milk"
        ]
        for cat in categories:
            st.markdown(f"- {cat}")

# Create tabs for Chat, Portfolio, and Resume
tab_chat, tab_portfolio, tab_resume = st.tabs(["Chat Assistant 💬", "My Portfolio 🌐", "My Resume 📄"])

with tab_chat:
    # Initialize the chat/session history in Streamlit session_state
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "ai", "content": "Hello! I'm your shopping assistant. How can I help you today?"}
        ]

    # Initialize upload variables
    uploaded_file = None
    go_ahead = False

    # Show the conversation history
    for idx, msg in enumerate(st.session_state["messages"]):
        if msg["role"] == "human":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
                
                # Keep the upload option below the first welcome message
                if idx == 0:
                    uploaded_file = st.file_uploader("Or upload a product image:", type=["jpg", "jpeg", "png"], key="welcome_image_uploader")
                    img_btn_disabled = uploaded_file is None
                    if uploaded_file is not None:
                        st.success("Image uploaded! Click 'Go ahead' to search.")
                    go_ahead = st.button("Go ahead", disabled=img_btn_disabled, key="welcome_go_ahead")

    # Streamlit chat input
    user_input = st.chat_input("What would you like to buy?")

    if go_ahead and uploaded_file is not None:
        shopping_agent = get_shopping_agent()
        from langchain_core.messages import AIMessage, HumanMessage
        
        # Save the uploaded image to a temporary file for processing
        suffix = "." + uploaded_file.name.split(".")[-1] if "." in uploaded_file.name else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_path = tmp_file.name

        # Add special message to the history for clarity and traceability
        msg_text = f"I have uploaded a product image. [Image path: {tmp_path}] Please analyze this image and find matching products."
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

        # Remove the temp file safely
        try:
            os.remove(tmp_path)
        except Exception:
            pass

        # Rerun to render updates cleanly
        st.rerun()

    elif user_input:
        shopping_agent = get_shopping_agent()
        from langchain_core.messages import AIMessage, HumanMessage

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

        # Rerun to render updates cleanly
        st.rerun()

with tab_portfolio:
    st.subheader("My Portfolio 🌐")
    st.markdown("Feel free to browse my personal portfolio directly below, or open it in a new window:")
    st.link_button("🌐 Open Portfolio Website", "https://vakul-singh.vercel.app/")
    st.components.v1.iframe("https://vakul-singh.vercel.app/", height=700, scrolling=True)

with tab_resume:
    st.subheader("My Resume 📄")
    st.markdown("Click the button below to view or download my resume from Google Drive:")
    st.link_button("📄 View Resume", "https://drive.google.com/drive/folders/1VfNSI8ek9rNOHqHo2R5Epx_67XMHbESk?usp=drive_link")