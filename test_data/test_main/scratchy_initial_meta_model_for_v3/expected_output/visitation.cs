/*
 * This code has been automatically generated by aas-core-csharp-codegen.
 * Do NOT edit or append.
 */

namespace AasCore.Aas3
{
    public static class Visitation
    {
        /// <summary>
        /// Define the interface for a visitor which visits the instances of the model.
        /// </summary>
        public interface IVisitor<T>
        {
            public T Visit(IEntity entity);
            public T Visit(LangString langString);
            public T Visit(LangStringSet langStringSet);
            public T Visit(Identifier identifier);
            public T Visit(AdministrativeInformation administrativeInformation);
            public T Visit(Key key);
            public T Visit(Reference reference);
            public T Visit(AssetAdministrationShell assetAdministrationShell);
        }  // public interface IVisitor

        /// <summary>
        /// Define the interface for a visitor which visits the instances of the model.
        /// </summary>
        /// <typeparam name="C">Context type</typeparam>
        /// <typeparam name="T">Result type</typeparam>
        public interface IVisitorWithContext<C, T>
        {
            public T Visit(IEntity entity, C context);
            public T Visit(LangString langString, C context);
            public T Visit(LangStringSet langStringSet, C context);
            public T Visit(Identifier identifier, C context);
            public T Visit(AdministrativeInformation administrativeInformation, C context);
            public T Visit(Key key, C context);
            public T Visit(Reference reference, C context);
            public T Visit(AssetAdministrationShell assetAdministrationShell, C context);
        }  // public interface IVisitorWithContext
    }  // public static class Visitation
}  // namespace AasCore.Aas3

/*
 * This code has been automatically generated by aas-core-csharp-codegen.
 * Do NOT edit or append.
 */
