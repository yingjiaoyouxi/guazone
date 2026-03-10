@echo off
echo ========================================
echo   瓜田守望者 GUA ZONE - 一键部署
echo ========================================
echo.
echo 方式1: 用 npx 部署到 Vercel (需要先运行 npx vercel login)
echo   cd guazone ^&^& npx vercel --prod --yes
echo.
echo 方式2: 用 GitHub Pages
echo   cd guazone ^&^& git init ^&^& git add . ^&^& git commit -m "init" ^&^& git branch -M main ^&^& git remote add origin https://github.com/YOUR_NAME/guazone.git ^&^& git push -u origin main
echo   然后在 GitHub 仓库 Settings ^> Pages 选择 main 分支
echo.
echo 方式3: 本地预览
echo   cd guazone ^&^& python -m http.server 8080
echo   然后浏览器打开 http://localhost:8080
echo.
echo ========================================
pause
