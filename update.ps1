# update.ps1 - Atalho para adicionar, commitar e enviar para o GitHub

param(
    # Define um parâmetro opcional para a mensagem do commit
    [Parameter(Mandatory=$false)]
    [string]$CommitMessage = "Atualiza projeto Clara" # Mensagem padrão se nenhuma for fornecida
)

Write-Host "Passo 1: Adicionando todos os arquivos modificados/novos..." -ForegroundColor Cyan
git add .

Write-Host "Passo 2: Fazendo commit com a mensagem: '$CommitMessage'..." -ForegroundColor Cyan
# Executa o commit. Se não houver nada para commitar, o Git avisará.
git commit -m "$CommitMessage"

# Verifica se o commit foi bem-sucedido antes de tentar o push
# ($? verifica se o último comando deu certo)
if ($?) {
    Write-Host "Passo 3: Enviando para o GitHub (origin master)..." -ForegroundColor Cyan
    git push origin master # Ou apenas 'git push' se o upstream já estiver configurado
} else {
    Write-Host "Commit falhou ou não havia nada para commitar. Push não realizado." -ForegroundColor Yellow
}

Write-Host "`n--- Atalho concluído! ---" -ForegroundColor Green
