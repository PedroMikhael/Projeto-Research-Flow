export const API_URL = "http://localhost:8000/api";

export const getToken = () => {
    if (typeof window !== "undefined") {
        return localStorage.getItem("research_flow_token");
    }
    return null;
};

export const setToken = (token: string) => {
    if (typeof window !== "undefined") {
        localStorage.setItem("research_flow_token", token);
    }
};

export const clearToken = () => {
    if (typeof window !== "undefined") {
        localStorage.removeItem("research_flow_token");
        // Also clear favorites cache
        localStorage.removeItem("researchFlowFavorites");
        localStorage.removeItem("researchFlowChatHistory");
    }
};

export async function loginUser(username, password) {
    const res = await fetch(`${API_URL}/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
        throw new Error("Credenciais inválidas");
    }
    const data = await res.json();
    return data; // Expected { token: "..." }
}

export async function registerUser(username, email, password) {
    const res = await fetch(`${API_URL}/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok) {
        const errorData = await res.json();
        const msg = JSON.stringify(errorData);
        throw new Error(msg || "Erro ao cadastrar");
    }
    return await res.json();
}

export async function logoutUser() {
    const token = getToken();
    if (token) {
        try {
            await fetch(`${API_URL}/logout/`, {
                method: "POST",
                headers: {
                    "Authorization": `Token ${token}`
                },
            });
        } catch (e) {
            console.error("Erro no logout backend", e);
        }
    }
    clearToken();
}
