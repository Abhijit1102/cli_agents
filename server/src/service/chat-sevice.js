import axios from "axios";

export class ChatService {
  constructor(baseUrl = "http://localhost:3000/api/conversations") {
    this.baseUrl = baseUrl;
  }

  /**
   * Create a new conversation
   */
  async createConversation(userId, mode = "chat", title) {
    const res = await axios.post(`${this.baseUrl}/create`, {
      userId,
      mode,
      title,
    });
    return res.data;
  }

  /**
   * Get or create conversation
   */
  async getOrCreateConversation(userId, conversationId, mode = "chat") {
    const params = { userId, mode };
    if (conversationId) params.conversationId = conversationId;

    const res = await axios.get(`${this.baseUrl}/get-or-create`, { params });
    return res.data;
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(userId, conversationId) {
    const res = await axios.delete(`${this.baseUrl}/delete`, {
      data: { userId, conversationId },
    });
    return res.data;
  }

  /**
   * List all conversations for a user
   */
  async listConversations(userId) {
    const res = await axios.get(`${this.baseUrl}/list`, {
      params: { userId },
    });
    return res.data;
  }

  /**
   * Add a message to a conversation
   */
  async addMessage(conversationId, role, content) {
    const res = await axios.post(`${this.baseUrl}/message`, {
      conversationId,
      role,
      content,
    });
    return res.data;
  }

  /**
   * Fetch messages of a conversation
   */
  async getMessages(conversationId) {
    const res = await axios.get(`${this.baseUrl}/message`, {
      params: { conversationId },
    });
    return res.data;
  }

  /**
   * Update conversation title
   */
  async updateTitle(conversationId, title) {
    const res = await axios.patch(`${this.baseUrl}/update-title`, {
      conversationId,
      title,
    });
    return res.data;
  }

   /**
   * Helper to parse content (JSON or string)
   */
  parseContent(content) {
    try {
      return JSON.parse(content);
    } catch {
      return content;
    }
  }

  /**
   * Format messages for AI SDK
   * @param {Array} messages - Database messages
   */
  formatMessagesForAI(messages) {
    return messages.map((msg) => ({
      role: msg.role,
      content: typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content),
    }));
  }

}
