Write-Host "Setting up SATURDAY AI OS Environment" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Check if Python is available
$pythonAvailable = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonAvailable) {
    Write-Host "Python not found in PATH. Attempting to locate Python..." -ForegroundColor Yellow
    
    # Look for Python in common locations
    $possiblePaths = @(
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe",
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe",
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python39\python.exe",
        "C:\Users\Administrator\AppData\Local\Programs\Python\Python38\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python39\python.exe",
        "C:\Python38\python.exe"
    )

    $pythonPath = $null
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $pythonPath = $path
            Write-Host "Found Python at: $path" -ForegroundColor Green
            break
        }
    }

    if (-not $pythonPath) {
        Write-Host "Python not found. Would recommend installing Python manually." -ForegroundColor Red
        Write-Host "Please install Python 3.8+ from python.org" -ForegroundColor Red
        exit 1
    } else {
        $pythonPath = $pythonPath
    }
} else {
    $pythonPath = "python"
}

Write-Host "Using Python: $pythonPath" -ForegroundColor Green

# Check if virtual environment exists
$venvPath = ".venv"
if (-not (Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $pythonPath -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
$venvPython = "$venvPath\Scripts\python.exe"
$venvPip = "$venvPath\Scripts\pip.exe"

Write-Host "Activating virtual environment..." -ForegroundColor Yellow

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
& $venvPip install --upgrade pip
& $venvPip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install requirements. Installing packages individually..." -ForegroundColor Yellow
    
    # Read requirements and install them one by one
    $requirements = Get-Content requirements.txt | Where-Object {$_ -notmatch "^#" -and $_ -notmatch "^\s*$"}
    foreach ($package in $requirements) {
        if ($package.Trim() -ne "") {
            Write-Host "Installing $package..." -ForegroundColor Yellow
            & $venvPip install $package
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Warning: Failed to install $package" -ForegroundColor Red
            }
        }
    }
}

# Verify and test core dependencies
Write-Host "Verifying and testing core dependencies..." -ForegroundColor Yellow

$coreModules = @(
    "fastapi",
    "uvicorn",
    "speech_recognition",
    "pygame",
    "tensorflow",
    "torch",
    "openai",
    "pyaudio",
    "llama_cpp",
    "sounddevice",
    "SpeechRecognition",
    "python_speech_features",
    "numpy",
    "scipy",
    "pandas",
    "psutil",
    "requests",
    "python-dotenv"
)

foreach ($module in $coreModules) {
    Write-Host "Testing $module..." -ForegroundColor Yellow
    try {
        & $venvPython -c "import $module"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "$module: OK" -ForegroundColor Green
        } else {
            Write-Host "$module: MISSING" -ForegroundColor Red
        }
    } catch {
        Write-Host "$module: ERROR - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Start SATURDAY in the background
Write-Host "Starting SATURDAY AI OS..." -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan

# Start the application in a background job
$appJob = Start-Job -ScriptBlock {
    param($venvPythonPath)
    & $venvPythonPath -m core.main
} -ArgumentList $venvPython

Write-Host "SATURDAY AI OS started in background job $($appJob.Id)" -ForegroundColor Green
Write-Host "Monitoring application..." -ForegroundColor Yellow

# Wait a moment for the app to start
Start-Sleep -Seconds 5

# Check if the job is still running
if ($appJob.State -eq "Running") {
    Write-Host "SATURDAY AI OS is running successfully!" -ForegroundColor Green
    Write-Host "Access the application at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Application started in the background." -ForegroundColor Green
    Write-Host "To check status, run: Get-Job -Id $($appJob.Id)" -ForegroundColor Yellow

    # Display running jobs
    Get-Job | Where-Object {$_.Id -eq $appJob.Id}
} else {
    Write-Host "SATURDAY AI OS failed to start properly." -ForegroundColor Red
    Receive-Job $appJob
}

Write-Host "`nTo stop the application, run: Stop-Job -Id $($appJob.Id); Remove-Job -Id $($appJob.Id)" -ForegroundColor Yellow
Write-Host "To check status, run: Get-Job -Id $($appJob.Id)" -ForegroundColor Yellow