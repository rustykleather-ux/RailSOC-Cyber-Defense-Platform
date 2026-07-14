import API from "../api";

export const getTrackBlocks = async () => {
    const response = await API.get("/track-blocks");
    return response.data;
};
