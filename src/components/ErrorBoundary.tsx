import React, { ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <div className="max-w-md w-full border-l-4 border-l-destructive bg-card p-6 rounded-standard">
            <h1 className="text-ia-section font-display font-semibold text-destructive mb-3">出错了</h1>
            <p className="text-ia-body text-ia-muted mb-5">
              {this.state.error?.message || '发生未知错误'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="cursor-pointer bg-primary text-primary-foreground px-4 py-2 rounded-standard text-ia-body font-medium transition-colors duration-150 hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:ring-offset-2 focus:ring-offset-card active:bg-primary/80"
            >
              刷新页面
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
