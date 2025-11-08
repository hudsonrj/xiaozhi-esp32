#!/usr/bin/env node
/**
 * Servidor MCP local para Portal da Transparência
 * Implementa protocolo JSON-RPC 2.0 via STDIO
 */

// API Key sempre configurada - usa valor padrão se não estiver na variável de ambiente
const PORTAL_API_KEY = process.env.PORTAL_API_KEY || '2c56919ba91b8c1b13473dcef43fb031';
const PORTAL_API_BASE = 'https://api.portaldatransparencia.gov.br/api-de-dados';

// Função auxiliar para fazer chamadas à API com header correto
async function callPortalApi(endpoint, params = {}) {
  const url = new URL(`${PORTAL_API_BASE}${endpoint}`);
  
  // Adicionar parâmetros à URL
  Object.keys(params).forEach(key => {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      url.searchParams.append(key, params[key]);
    }
  });
  
  // Fazer requisição com header correto
  const response = await fetch(url.toString(), {
    headers: {
      'chave-api-dados': PORTAL_API_KEY,
      'Accept': 'application/json'
    }
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Erro na API do Portal (${response.status}): ${errorText}`);
  }
  
  return await response.json();
}

// Lista de ferramentas principais do Portal da Transparência
const tools = [
  {
    name: 'portal_check_api_key',
    description: 'Verifica se a API key do Portal da Transparência está configurada',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'portal_servidores_consultar',
    description: 'Consulta dados de servidores públicos do Poder Executivo Federal',
    inputSchema: {
      type: 'object',
      properties: {
        orgaoServidorLotacao: { type: 'string', description: 'Código do órgão' },
        nome: { type: 'string', description: 'Nome do servidor' },
        cpf: { type: 'string', description: 'CPF do servidor' },
        pagina: { type: 'number', description: 'Número da página', default: 1 },
        tamanhoPagina: { type: 'number', description: 'Tamanho da página', default: 10 },
      },
    },
  },
  {
    name: 'portal_viagens_consultar',
    description: 'Consulta viagens a serviço',
    inputSchema: {
      type: 'object',
      properties: {
        dataIdaDe: { type: 'string', description: 'Data de ida (DD/MM/AAAA)' },
        dataIdaAte: { type: 'string', description: 'Data de ida até (DD/MM/AAAA)' },
        codigoOrgao: { type: 'string', description: 'Código do órgão' },
        pagina: { type: 'number', description: 'Número da página', default: 1 },
        tamanhoPagina: { type: 'number', description: 'Tamanho da página', default: 10 },
      },
    },
  },
  {
    name: 'portal_contratos_consultar',
    description: 'Consulta contratos do Poder Executivo Federal',
    inputSchema: {
      type: 'object',
      properties: {
        dataAssinaturaDe: { type: 'string', description: 'Data de assinatura inicial (DD/MM/AAAA)' },
        dataAssinaturaAte: { type: 'string', description: 'Data de assinatura final (DD/MM/AAAA)' },
        codigoOrgao: { type: 'string', description: 'Código do órgão' },
        pagina: { type: 'number', description: 'Número da página', default: 1 },
        tamanhoPagina: { type: 'number', description: 'Tamanho da página', default: 10 },
      },
    },
  },
  {
    name: 'portal_despesas_consultar',
    description: 'Consulta despesas públicas',
    inputSchema: {
      type: 'object',
      properties: {
        dataEmissaoDe: { type: 'string', description: 'Data de emissão inicial (DD/MM/AAAA)' },
        dataEmissaoAte: { type: 'string', description: 'Data de emissão final (DD/MM/AAAA)' },
        codigoOrgao: { type: 'string', description: 'Código do órgão' },
        pagina: { type: 'number', description: 'Número da página', default: 1 },
        tamanhoPagina: { type: 'number', description: 'Tamanho da página', default: 10 },
      },
    },
  },
  {
    name: 'portal_beneficios_consultar',
    description: 'Consulta programas sociais e beneficiários',
    inputSchema: {
      type: 'object',
      properties: {
        codigoPrograma: { type: 'string', description: 'Código do programa social' },
        nis: { type: 'string', description: 'Número de Identificação Social (NIS)' },
        pagina: { type: 'number', description: 'Número da página', default: 1 },
        tamanhoPagina: { type: 'number', description: 'Tamanho da página', default: 10 },
      },
    },
  },
  {
    name: 'portal_licitacoes_consultar',
    description: 'Consulta processos licitatórios',
    inputSchema: {
      type: 'object',
      properties: {
        dataInicial: { type: 'string', description: 'Data inicial (DD/MM/AAAA)' },
        dataFinal: { type: 'string', description: 'Data final (DD/MM/AAAA)' },
        codigoOrgao: { type: 'string', description: 'Código do órgão' },
        pagina: { type: 'number', description: 'Número da página', default: 1 },
        tamanhoPagina: { type: 'number', description: 'Tamanho da página', default: 10 },
      },
    },
  },
];

// Buffer para ler mensagens linha por linha
let buffer = '';

// Ler stdin linha por linha
process.stdin.setEncoding('utf8');

process.stdin.on('data', async (chunk) => {
  buffer += chunk;
  
  // Processar linhas completas
  const lines = buffer.split('\n');
  buffer = lines.pop() || ''; // Manter última linha incompleta no buffer
  
  for (const line of lines) {
    if (line.trim()) {
      await handleMessage(line.trim());
    }
  }
});

process.stdin.on('end', () => {
  process.exit(0);
});

async function handleMessage(line) {
  try {
    const message = JSON.parse(line);
    
    // Responder ao initialize
    if (message.method === 'initialize') {
      const response = {
        jsonrpc: '2.0',
        id: message.id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {},
          },
          serverInfo: {
            name: 'portal-transparencia',
            version: '1.0.0',
          },
        },
      };
      console.log(JSON.stringify(response));
      return;
    }
    
    // Responder ao tools/list
    if (message.method === 'tools/list') {
      const response = {
        jsonrpc: '2.0',
        id: message.id,
        result: {
          tools: tools,
        },
      };
      console.log(JSON.stringify(response));
      return;
    }
    
    // Responder ao tools/call
    if (message.method === 'tools/call') {
      const { name, arguments: args } = message.params;
      
      try {
        let result;
        
        switch (name) {
          case 'portal_check_api_key':
            // API Key sempre está configurada (tem valor padrão)
            result = {
              content: [
                {
                  type: 'text',
                  text: `API Key configurada e pronta para uso: ${PORTAL_API_KEY.substring(0, 10)}...`,
                },
              ],
            };
            break;
            
          case 'portal_servidores_consultar': {
            const apiParams = {};
            if (args.orgaoServidorLotacao) apiParams.orgaoServidorLotacao = args.orgaoServidorLotacao;
            if (args.nome) apiParams.nome = args.nome;
            if (args.cpf) apiParams.cpf = args.cpf;
            if (args.pagina) apiParams.pagina = args.pagina;
            if (args.tamanhoPagina) apiParams.tamanhoPagina = args.tamanhoPagina;
            
            const data = await callPortalApi('/servidores', apiParams);
            result = {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(data, null, 2),
                },
              ],
            };
            break;
          }
          
          case 'portal_viagens_consultar': {
            const apiParams = {};
            if (args.dataIdaDe) apiParams.dataIdaDe = args.dataIdaDe;
            if (args.dataIdaAte) apiParams.dataIdaAte = args.dataIdaAte;
            if (args.codigoOrgao) apiParams.codigoOrgao = args.codigoOrgao;
            if (args.pagina) apiParams.pagina = args.pagina;
            if (args.tamanhoPagina) apiParams.tamanhoPagina = args.tamanhoPagina;
            
            const data = await callPortalApi('/viagens', apiParams);
            result = {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(data, null, 2),
                },
              ],
            };
            break;
          }
          
          case 'portal_contratos_consultar': {
            const apiParams = {};
            if (args.dataAssinaturaDe) apiParams.dataAssinaturaDe = args.dataAssinaturaDe;
            if (args.dataAssinaturaAte) apiParams.dataAssinaturaAte = args.dataAssinaturaAte;
            if (args.codigoOrgao) apiParams.codigoOrgao = args.codigoOrgao;
            if (args.pagina) apiParams.pagina = args.pagina;
            if (args.tamanhoPagina) apiParams.tamanhoPagina = args.tamanhoPagina;
            
            const data = await callPortalApi('/contratos', apiParams);
            result = {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(data, null, 2),
                },
              ],
            };
            break;
          }
          
          case 'portal_despesas_consultar': {
            const apiParams = {};
            if (args.dataEmissaoDe) apiParams.dataEmissaoDe = args.dataEmissaoDe;
            if (args.dataEmissaoAte) apiParams.dataEmissaoAte = args.dataEmissaoAte;
            if (args.codigoOrgao) apiParams.codigoOrgao = args.codigoOrgao;
            if (args.pagina) apiParams.pagina = args.pagina;
            if (args.tamanhoPagina) apiParams.tamanhoPagina = args.tamanhoPagina;
            
            const data = await callPortalApi('/despesas', apiParams);
            result = {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(data, null, 2),
                },
              ],
            };
            break;
          }
          
          case 'portal_beneficios_consultar': {
            const apiParams = {};
            if (args.codigoPrograma) apiParams.codigoPrograma = args.codigoPrograma;
            if (args.nis) apiParams.nis = args.nis;
            if (args.pagina) apiParams.pagina = args.pagina;
            if (args.tamanhoPagina) apiParams.tamanhoPagina = args.tamanhoPagina;
            
            const data = await callPortalApi('/beneficios', apiParams);
            result = {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(data, null, 2),
                },
              ],
            };
            break;
          }
          
          case 'portal_licitacoes_consultar': {
            const apiParams = {};
            if (args.dataInicial) apiParams.dataInicial = args.dataInicial;
            if (args.dataFinal) apiParams.dataFinal = args.dataFinal;
            if (args.codigoOrgao) apiParams.codigoOrgao = args.codigoOrgao;
            if (args.pagina) apiParams.pagina = args.pagina;
            if (args.tamanhoPagina) apiParams.tamanhoPagina = args.tamanhoPagina;
            
            const data = await callPortalApi('/licitacoes', apiParams);
            result = {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(data, null, 2),
                },
              ],
            };
            break;
          }
          
          default:
            throw new Error(`Ferramenta desconhecida: ${name}`);
        }
        
        const response = {
          jsonrpc: '2.0',
          id: message.id,
          result: result,
        };
        console.log(JSON.stringify(response));
        
      } catch (error) {
        const errorResponse = {
          jsonrpc: '2.0',
          id: message.id,
          error: {
            code: -32000,
            message: `Erro ao executar ferramenta ${name}: ${error.message}`,
          },
        };
        console.log(JSON.stringify(errorResponse));
      }
      return;
    }
    
    // Método não implementado
    const errorResponse = {
      jsonrpc: '2.0',
      id: message.id,
      error: {
        code: -32601,
        message: `Método não implementado: ${message.method}`,
      },
    };
    console.log(JSON.stringify(errorResponse));
    
  } catch (error) {
    // Erro ao processar mensagem
    const errorResponse = {
      jsonrpc: '2.0',
      id: null,
      error: {
        code: -32700,
        message: `Erro ao processar mensagem: ${error.message}`,
      },
    };
    console.log(JSON.stringify(errorResponse));
  }
}

// Enviar mensagem de erro para stderr (não quebra o protocolo)
process.stderr.write('Servidor MCP Portal da Transparência iniciado\n');
