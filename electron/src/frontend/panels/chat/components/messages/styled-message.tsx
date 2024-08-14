import { useState } from 'react'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { CodeBlock } from '@/components/ui/codeblock'
import { MemoizedReactMarkdown } from '../ui/memoized-react-markdown'
import { getLanguageFromFilename } from '@/lib/programming-language-utils'
import { getFileName } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Check, X } from 'lucide-react'
import './markdown.css'

const StyledMessage = ({
    content,
    className,
    icon,
    onYesNoAnswer,
}: {
    content: string
    className?: string
    icon: React.ReactNode
    onYesNoAnswer?: (question: string, answer: string) => void
}) => {
    const path = extractPath(content)
    const { contentParts } = parseContent(content)

    return (
        <div className={cn('group relative flex items-start', className)}>
            {icon}
            <div className="ml-4 flex-1 space-y-2 overflow-hidden px-1">
                {path && (
                    <div className="text-sm text-gray-500 mb-2">
                        <strong>Path:</strong> {path}
                    </div>
                )}
                <div className="space-y-4">
                    {contentParts.map((part, index) => {
                        if (part.type === 'markdown') {
                            return (
                                <MemoizedReactMarkdown
                                    key={index}
                                    className="markdown prose break-words dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 chat-text-relaxed"
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        p({ children }) {
                                            return (
                                                <p className="mb-2 last:mb-0 whitespace-pre-wrap">
                                                    {children}
                                                </p>
                                            )
                                        },
                                        code({
                                            node,
                                            className,
                                            children,
                                            ...props
                                        }) {
                                            const value = String(
                                                children
                                            ).replace(/\n$/, '')
                                            const languageMatch =
                                                /language-(\w+)/.exec(
                                                    className || ''
                                                )
                                            const lang = languageMatch
                                                ? languageMatch[1]
                                                : ''

                                            if (
                                                value.split('\n').length ===
                                                    1 &&
                                                !props.meta
                                            ) {
                                                return (
                                                    <code
                                                        className={cn(
                                                            className
                                                        )}
                                                        {...props}
                                                    >
                                                        {value}
                                                    </code>
                                                )
                                            }

                                            const match = /language-(\w+)/.exec(
                                                className || ''
                                            )
                                            const meta = props.meta || ''
                                            return (
                                                <div className="relative py-5">
                                                    {meta && (
                                                        <div className="text-sm text-gray-500 mb-2">
                                                            <strong>
                                                                Command:
                                                            </strong>{' '}
                                                            {meta}
                                                        </div>
                                                    )}
                                                    <CodeBlock
                                                        key={Math.random()}
                                                        value={value}
                                                        language={lang}
                                                    />
                                                </div>
                                            )
                                        },
                                    }}
                                >
                                    {part.content}
                                </MemoizedReactMarkdown>
                            )
                        } else if (part.type === 'yesNoQuestion') {
                            return (
                                <YesNoQuestion
                                    key={index}
                                    question={part.content}
                                    onAnswer={answer =>
                                        onYesNoAnswer &&
                                        onYesNoAnswer(part.content, answer)
                                    }
                                />
                            )
                        } else if (part.type === 'list') {
                            return (
                                <ListDisplay
                                    key={index}
                                    content={part.content}
                                    title={part.title}
                                />
                            )
                        } else if (part.type === 'codeBlock') {
                            return (
                                <div key={index} className="relative py-5">
                                    <pre className="text-md mb-2">
                                        <strong>Command:</strong> {part.command}{' '}
                                        {part.relativePath}
                                    </pre>
                                    <CodeBlock
                                        value={part.code}
                                        fileName={part.fileName}
                                        language={
                                            part.fileName
                                                ? getLanguageFromFilename(
                                                      part.fileName
                                                  ) ?? 'plaintext'
                                                : 'plaintext'
                                        }
                                    />
                                </div>
                            )
                        }
                    })}
                </div>
            </div>
        </div>
    )
}

const extractPath = (content: string) => {
    const pathMatch = content.match(/^# (\/[^\s]+)/)
    if (pathMatch) {
        return pathMatch[1]
    }
    return null
}

const parseContent = (content: string) => {
    const contentParts = []
    let currentText = ''

    const pushCurrentText = () => {
        if (currentText.trim()) {
            contentParts.push({ type: 'markdown', content: currentText.trim() })
            currentText = ''
        }
    }

    const processYesNoQuestion = (match, fullText) => {
        const before = fullText.slice(0, match.index)
        const after = fullText.slice(match.index + match[0].length)

        if (before.trim()) {
            contentParts.push({ type: 'markdown', content: before.trim() })
        }

        contentParts.push({ type: 'yesNoQuestion', content: match[1] })

        return after
    }

    const processList = (match, fullText) => {
        const before = fullText.slice(0, match.index)
        const after = fullText.slice(match.index + match[0].length)

        if (before.trim()) {
            contentParts.push({ type: 'markdown', content: before.trim() })
        }

        const listContent = match[1].trim()
        const lines = listContent.split('\n').map(item => item.trim())
        const title = lines[0]
        const items = lines.slice(1).join('\n')

        contentParts.push({ type: 'list', title, content: items })

        return after
    }

    let remainingContent = content
    while (remainingContent.length > 0) {
        const codeBlockMatch = remainingContent.match(
            /Running command: (\S+)\s+(\S+)\s+<<<\n([\s\S]*?)\n>>>/
        )
        const yesNoMatch = remainingContent.match(
            /<YES_NO_QUESTION>([\s\S]*?)<\/YES_NO_QUESTION>/
        )
        const listMatch = remainingContent.match(/<LIST>([\s\S]*?)<\/LIST>/)

        if (
            codeBlockMatch &&
            (!yesNoMatch || codeBlockMatch.index < yesNoMatch.index) &&
            (!listMatch || codeBlockMatch.index < listMatch.index)
        ) {
            pushCurrentText()
            contentParts.push({
                type: 'codeBlock',
                command: codeBlockMatch[1],
                relativePath: codeBlockMatch[2],
                fileName: getFileName(codeBlockMatch[2]),
                code: codeBlockMatch[3].trim(),
            })
            remainingContent = remainingContent.slice(
                codeBlockMatch.index + codeBlockMatch[0].length
            )
        } else if (
            yesNoMatch &&
            (!listMatch || yesNoMatch.index < listMatch.index)
        ) {
            remainingContent = processYesNoQuestion(
                yesNoMatch,
                remainingContent
            )
        } else if (listMatch) {
            remainingContent = processList(listMatch, remainingContent)
        } else {
            currentText += remainingContent
            remainingContent = ''
        }
    }

    pushCurrentText()

    return { contentParts }
}

const YesNoQuestion = ({
    question,
    onAnswer,
}: {
    question: string
    onAnswer: (answer: string) => void
}) => {
    const [answered, setAnswered] = useState<'yes' | 'no' | boolean>(false)

    const handleAnswer = (answer: 'yes' | 'no') => {
        setAnswered(answer)
        onAnswer(answer)
    }

    return (
        <div className="p-4 rounded-lg border-2 border-outlinecolor bg-midnight">
            <p
                className={`font-medium chat-text-relaxed flex ${
                    answered === false ? 'mb-4' : 'mb-0'
                }`}
            >
                {question}
                {answered === 'yes' ? (
                    <Check
                        size={16}
                        className="ml-auto text-green-500 flex-shrink-0 mt-1"
                    />
                ) : answered === 'no' ? (
                    <X
                        size={16}
                        className="ml-auto text-red-500 flex-shrink-0 mt-1"
                    />
                ) : null}
            </p>
            {answered === false && (
                <div className="flex space-x-3">
                    <OutlineButton
                        className="border-[#38662A] bg-[#294122] hover:bg-[#38662A]"
                        onClick={() => handleAnswer('yes')}
                    >
                        <Check size={16} />
                    </OutlineButton>

                    <OutlineButton
                        className="border-[#772C22] bg-[#4A1F23] hover:bg-[#772C22]"
                        onClick={() => handleAnswer('no')}
                    >
                        <X size={16} />
                    </OutlineButton>
                </div>
            )}
        </div>
    )
}

const OutlineButton = ({
    className,
    children,
    onClick,
}: {
    className?: string
    children: React.ReactNode
    onClick: () => void
}) => {
    return (
        <Button
            className={cn(
                'h-9 p-[5px] rounded-lg items-center flex justify-center',
                className
            )}
            variant="outline"
            onClick={onClick}
        >
            {children}
        </Button>
    )
}

const ListDisplay = ({
    content,
    title,
}: {
    content: string
    title: string
}) => {
    return (
        <div className="p-4 rounded-lg border-2 border-outlinecolor bg-midnight">
            {title && (
                <h3 className="font-semibold mb-3 text-[1.1rem] chat-text-relaxed">
                    {title}
                </h3>
            )}
            <MemoizedReactMarkdown
                className="markdown chat-text-relaxed"
                remarkPlugins={[remarkGfm]}
                components={{
                    p: ({ node, ...props }) => (
                        <p className="whitespace-pre-wrap" {...props} />
                    ),
                }}
            >
                {content}
            </MemoizedReactMarkdown>
        </div>
    )
}

export default StyledMessage
