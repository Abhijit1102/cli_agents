import axios from "axios";

export const getMe = async (token) => {
  const res = await axios.get("http://localhost:3000/api/me", {
    headers: {
      Authorization: `Bearer ${token.access_token}`,
    },
  });
  return res.data;
};
