import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
export const useHealth = () => useQuery({queryKey:["health"], queryFn:api.health, refetchInterval:15000});
export const useModel = () => useQuery({queryKey:["model"], queryFn:api.modelInfo});
export const useDecisions = () => useQuery({queryKey:["decisions"], queryFn:api.decisions});
