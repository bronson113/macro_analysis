import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getNestedMarkdownHeadingLevel } from '../utils/markdownHeadings';

const MarkdownHeading = ({ children, node: _node, sourceLevel, ...props }) => {
  const Heading = `h${getNestedMarkdownHeadingLevel(sourceLevel)}`;

  return <Heading {...props}>{children}</Heading>;
};

const markdownComponents = {
  h1: props => <MarkdownHeading {...props} sourceLevel={1} />,
  h2: props => <MarkdownHeading {...props} sourceLevel={2} />,
  h3: props => <MarkdownHeading {...props} sourceLevel={3} />,
  h4: props => <MarkdownHeading {...props} sourceLevel={4} />,
  h5: props => <MarkdownHeading {...props} sourceLevel={5} />,
  h6: props => <MarkdownHeading {...props} sourceLevel={6} />,
  table: ({ children }) => <div className="markdown-table-scroll"><table>{children}</table></div>,
};

const MarkdownContent = ({ content }) => (
  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
    {content}
  </ReactMarkdown>
);

export default MarkdownContent;
