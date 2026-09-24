from celery import shared_task
import time

@shared_task
def tarefa_pesada_simulada(nome_usuario):
    print(f"📦 INICIO: Processando dados para {nome_usuario}...")
    
    time.sleep(10) 
    print(f"✅ FIM: Dados de {nome_usuario} processados com sucesso!")
    return f"Relatório de {nome_usuario} gerado."